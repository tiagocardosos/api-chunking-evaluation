import time

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI

from core.config import settings
from core.embeddings import OpenAIEmbedder
from core.vector_store import VectorStore
from models.enums import RetrievalStrategy
from models.schemas import RagChatRequest, RagChatResponse, SearchResult

router = APIRouter()

# Prompt do sistema: fixado para reproducibilidade do experimento.
# Temperatura = 0 garante respostas determinísticas para o mesmo contexto.
_SYSTEM_PROMPT = """Você é um assistente especializado em documentos institucionais brasileiros \
(editais EMBRAPII, currículos Lattes CNPq).

Instruções:
- Responda APENAS com base no contexto fornecido.
- Se a resposta não estiver no contexto, responda exatamente: \
"Informação não encontrada no contexto fornecido."
- Seja conciso, preciso e cite o trecho relevante quando possível.
- Responda em português do Brasil."""


def get_vector_store() -> VectorStore:
    return VectorStore()


@router.post("/chat", response_model=RagChatResponse)
def rag_chat(
    body: RagChatRequest,
    vs: VectorStore = Depends(get_vector_store),
):
    """
    Pipeline RAG completo: recuperação + geração.

    1. Embed da query via OpenAI.
    2. Recupera top_k chunks do Qdrant (semântico ou híbrido).
    3. Monta o prompt com o contexto recuperado.
    4. Gera resposta com GPT-4o-mini (temperatura=0, determinístico).
    5. Retorna resposta + contexto + latência em ms.
    """
    if not vs.collection_exists(body.collection_id):
        raise HTTPException(
            status_code=404,
            detail=f"Coleção {body.collection_id!r} não encontrada. "
                   "Ingira documentos antes de consultar.",
        )

    start = time.monotonic()

    # ── 1. Recuperação ────────────────────────────────────────────────────────
    embedder = OpenAIEmbedder()
    query_vector = embedder.embed_query(body.query)

    if body.retrieval_strategy == RetrievalStrategy.hybrid:
        hits = vs.search_hybrid(
            collection_name=body.collection_id,
            query_vector=query_vector,
            query_text=body.query,
            top_k=body.top_k,
        )
    else:
        hits = vs.search_semantic(
            collection_name=body.collection_id,
            query_vector=query_vector,
            top_k=body.top_k,
        )

    if not hits:
        raise HTTPException(
            status_code=404,
            detail="Nenhum chunk recuperado. Verifique se a coleção tem documentos indexados.",
        )

    # ── 2. Montagem do contexto ───────────────────────────────────────────────
    context_blocks = [
        f"[Trecho {i + 1}]\n{hit.content}"
        for i, hit in enumerate(hits)
    ]
    context_text = "\n\n---\n\n".join(context_blocks)

    # ── 3. Geração ────────────────────────────────────────────────────────────
    generator_model = body.generator_model or settings.generator_model
    answer = _generate(
        query=body.query,
        context=context_text,
        model=generator_model,
    )

    latency_ms = round((time.monotonic() - start) * 1000, 2)

    return RagChatResponse(
        query=body.query,
        answer=answer,
        context=[
            SearchResult(
                chunk_id=hit.chunk_id,
                content=hit.content,
                score=hit.score,
                chunk_metadata=hit.chunk_metadata,
            )
            for hit in hits
        ],
        latency_ms=latency_ms,
    )


def _generate(query: str, context: str, model: str) -> str:
    """
    Chama a API OpenAI Chat Completions com temperatura=0.

    Temperature=0 é obrigatório para reproducibilidade do experimento:
    garante que a mesma query + contexto produzam sempre a mesma resposta.
    """
    client = OpenAI(api_key=settings.openai_api_key)

    user_prompt = f"Contexto:\n{context}\n\nPergunta: {query}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        seed=42,  # seed adicional para máxima reproducibilidade
    )

    return response.choices[0].message.content or ""
