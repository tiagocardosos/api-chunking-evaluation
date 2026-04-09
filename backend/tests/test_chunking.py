"""
Testes das estratégias de chunking.

Execução:
    cd backend && uv run pytest tests/test_chunking.py -v

Notas:
    - SemanticChunker usa mock de embeddings (evita baixar modelo).
    - StructureAwareChunker tem fixture de XML Lattes mínimo real.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Garante que o backend está no path
sys.path.insert(0, str(Path(__file__).parent.parent))

import core.chunking  # noqa: F401 — registra todos os chunkers

from core.chunking.base import ChunkData
from core.chunking.fixed_size import FixedSizeChunker
from core.chunking.recursive import RecursiveCharacterChunker
from core.chunking.registry import get_chunker, list_strategies
from core.chunking.sentence import SentenceChunker, split_sentences
from core.chunking.semantic import SemanticChunker
from core.chunking.structure_aware import StructureAwareChunker
from models.enums import ChunkingStrategy

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_PT_TEXT = """
A inteligência artificial tem transformado profundamente a sociedade contemporânea.
Sistemas de aprendizado de máquina são aplicados em diagnósticos médicos, veículos autônomos e finanças.
No Brasil, pesquisadores da USP e da UNICAMP lideram estudos sobre processamento de linguagem natural.
O Prof. Dr. Alan Turing é considerado o pai da computação moderna.
Recuperação aumentada por geração, conhecida como RAG, combina busca e geração de texto.
Experimentos controlados com métricas RAGAS permitem comparar estratégias de chunking de forma objetiva.
A estratégia structure-aware é especialmente útil para documentos estruturados como currículos Lattes.
Resultados preliminares indicam superioridade do chunking semântico em perguntas inferenciais.
"""

SAMPLE_XML_LATTES = """<?xml version="1.0" encoding="ISO-8859-1"?>
<CURRICULO-VITAE DATA-ATUALIZACAO="01/01/2024" HORA-ATUALIZACAO="10:00">
  <DADOS-GERAIS
    NOME-COMPLETO="Maria Silva Santos"
    PAIS-DE-NASCIMENTO="Brasil"
    GRANDE-AREA-DO-CONHECIMENTO="Ciências Exatas e da Terra"
    AREA-DO-CONHECIMENTO="Ciência da Computação"
    RESUMO-CV="Pesquisadora em NLP e IA com foco em recuperação de informação."
  />
  <FORMACAO-ACADEMICA-TITULACAO>
    <DOUTORADO
      NOME-CURSO="Ciência da Computação"
      ANO-DE-INICIO="2018"
      ANO-DE-CONCLUSAO="2022"
      NOME-INSTITUICAO="Universidade de São Paulo"
      TITULO-DA-TESE-DISSERTACAO="Chunking Semântico para RAG em Português"
    />
    <MESTRADO
      NOME-CURSO="Ciência da Computação"
      ANO-DE-INICIO="2016"
      ANO-DE-CONCLUSAO="2018"
      NOME-INSTITUICAO="UNICAMP"
    />
  </FORMACAO-ACADEMICA-TITULACAO>
  <PRODUCAO-BIBLIOGRAFICA>
    <ARTIGOS-PUBLICADOS>
      <ARTIGO-PUBLICADO>
        <DADOS-BASICOS-DO-ARTIGO
          TITULO="Avaliação de Estratégias de Chunking em RAG"
          ANO="2023"
          PAIS-DE-PUBLICACAO="Brasil"
        />
        <DETALHAMENTO-DO-ARTIGO
          NOME-DO-PERIODICO="Journal of Artificial Intelligence Research"
          VOLUME="45"
          PAGINA-INICIAL="100"
          PAGINA-FINAL="120"
        />
        <AUTORES
          NOME-COMPLETO="Maria Silva Santos"
          ORDEM-DE-AUTORIA="1"
        />
        <AUTORES
          NOME-COMPLETO="João Pedro Oliveira"
          ORDEM-DE-AUTORIA="2"
        />
      </ARTIGO-PUBLICADO>
      <ARTIGO-PUBLICADO>
        <DADOS-BASICOS-DO-ARTIGO
          TITULO="Embeddings Multilíngues para Documentos Brasileiros"
          ANO="2022"
        />
        <DETALHAMENTO-DO-ARTIGO
          NOME-DO-PERIODICO="Revista Brasileira de Informática"
        />
        <AUTORES NOME-COMPLETO="Maria Silva Santos" ORDEM-DE-AUTORIA="1"/>
      </ARTIGO-PUBLICADO>
    </ARTIGOS-PUBLICADOS>
    <LIVROS-E-CAPITULOS>
      <LIVROS-PUBLICADOS-OU-ORGANIZADOS>
        <LIVRO-PUBLICADO-OU-ORGANIZADO>
          <DADOS-BASICOS-DO-LIVRO
            TITULO="Fundamentos de RAG em Português"
            ANO="2023"
          />
          <DETALHAMENTO-DO-LIVRO NUMERO-DE-PAGINAS="320" EDITORA="Editora UNESP"/>
          <AUTORES NOME-COMPLETO="Maria Silva Santos" ORDEM-DE-AUTORIA="1"/>
        </LIVRO-PUBLICADO-OU-ORGANIZADO>
      </LIVROS-PUBLICADOS-OU-ORGANIZADOS>
    </LIVROS-E-CAPITULOS>
  </PRODUCAO-BIBLIOGRAFICA>
</CURRICULO-VITAE>
"""


# ── Registry ──────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_all_strategies_registered(self):
        strategies = list_strategies()
        expected = {s.value for s in ChunkingStrategy}
        assert expected.issubset(set(strategies)), (
            f"Estratégias não registradas: {expected - set(strategies)}"
        )

    def test_get_chunker_returns_correct_type(self):
        chunker = get_chunker(ChunkingStrategy.fixed_size, chunk_size=256)
        assert isinstance(chunker, FixedSizeChunker)

    def test_get_chunker_unknown_raises(self):
        with pytest.raises(ValueError, match="Estratégia desconhecida"):
            get_chunker("nao_existe")


# ── FixedSizeChunker ──────────────────────────────────────────────────────────

class TestFixedSizeChunker:
    def test_basic_split(self):
        chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=0)
        chunks = chunker.split(SAMPLE_PT_TEXT)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.content) <= 100
            assert chunk.content.strip()

    def test_overlap_creates_extra_chunks(self):
        chunker_no_overlap = FixedSizeChunker(chunk_size=200, chunk_overlap=0)
        chunker_overlap = FixedSizeChunker(chunk_size=200, chunk_overlap=50)
        no_ov = chunker_no_overlap.split(SAMPLE_PT_TEXT)
        with_ov = chunker_overlap.split(SAMPLE_PT_TEXT)
        assert len(with_ov) >= len(no_ov)

    def test_chunks_are_indexed_sequentially(self):
        chunks = FixedSizeChunker(chunk_size=100).split(SAMPLE_PT_TEXT)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_metadata_contains_required_keys(self):
        chunks = FixedSizeChunker().split(SAMPLE_PT_TEXT)
        for chunk in chunks:
            assert chunk.metadata["strategy"] == ChunkingStrategy.fixed_size.value
            assert "start_char" in chunk.metadata
            assert "end_char" in chunk.metadata

    def test_empty_text_returns_empty(self):
        assert FixedSizeChunker().split("") == []
        assert FixedSizeChunker().split("   ") == []

    def test_invalid_overlap_raises(self):
        with pytest.raises(ValueError):
            FixedSizeChunker(chunk_size=100, chunk_overlap=100)

    @pytest.mark.parametrize("chunk_size,overlap", [
        (256, 0), (256, 50), (512, 50), (512, 128), (1024, 128)
    ])
    def test_experiment_configurations(self, chunk_size, overlap):
        """Valida todas as configurações usadas no experimento (EXPERIMENT-SPEC §3)."""
        chunks = FixedSizeChunker(chunk_size=chunk_size, chunk_overlap=overlap).split(
            SAMPLE_PT_TEXT * 5  # texto mais longo para garantir múltiplos chunks
        )
        assert len(chunks) > 0
        for c in chunks:
            assert len(c.content) <= chunk_size


# ── RecursiveCharacterChunker ─────────────────────────────────────────────────

class TestRecursiveCharacterChunker:
    def test_prefers_paragraph_splits(self):
        text = "Parágrafo um.\n\nParágrafo dois.\n\nParágrafo três."
        chunks = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=0).split(text)
        # Cada parágrafo deve ficar em seu próprio chunk (todos < 50 chars)
        assert len(chunks) == 3

    def test_falls_back_to_sentence_split(self):
        # Parágrafo único longo: deve dividir por '.'
        text = "Primeira frase do texto. Segunda frase do texto. Terceira frase do texto."
        chunks = RecursiveCharacterChunker(chunk_size=35, chunk_overlap=0).split(text)
        assert len(chunks) > 1

    def test_chunk_size_respected(self):
        chunks = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=0).split(
            SAMPLE_PT_TEXT
        )
        for c in chunks:
            # LangChain pode ultrapassar chunk_size em casos extremos (sem separador disponível)
            # mas deve ser próximo
            assert len(c.content) <= 150  # margem de segurança

    def test_metadata_strategy_name(self):
        chunks = RecursiveCharacterChunker().split(SAMPLE_PT_TEXT)
        for c in chunks:
            assert c.metadata["strategy"] == ChunkingStrategy.recursive.value

    def test_empty_text_returns_empty(self):
        assert RecursiveCharacterChunker().split("") == []


# ── SentenceChunker ───────────────────────────────────────────────────────────

class TestSplitSentences:
    def test_basic_sentence_split(self):
        text = "Primeira frase. Segunda frase. Terceira frase."
        sentences = split_sentences(text)
        assert len(sentences) == 3

    def test_abbreviation_not_split(self):
        text = "O Prof. Dr. Silva apresentou o trabalho. Foi bem recebido."
        sentences = split_sentences(text)
        # "Prof. Dr." não devem gerar quebras
        assert len(sentences) == 2

    def test_exclamation_and_question(self):
        text = "Que resultado surpreendente! Você esperava isso? Eu também não."
        sentences = split_sentences(text)
        assert len(sentences) == 3


class TestSentenceChunker:
    def test_sentences_not_broken(self):
        chunker = SentenceChunker(max_chunk_size=200)
        chunks = chunker.split(SAMPLE_PT_TEXT)
        # Nenhum chunk deve terminar no meio de uma palavra
        for c in chunks:
            assert c.content == c.content.strip()

    def test_overlap_sentences(self):
        chunker_no_ov = SentenceChunker(max_chunk_size=150, overlap_sentences=0)
        chunker_ov = SentenceChunker(max_chunk_size=150, overlap_sentences=2)
        no_ov = chunker_no_ov.split(SAMPLE_PT_TEXT)
        with_ov = chunker_ov.split(SAMPLE_PT_TEXT)
        assert len(with_ov) >= len(no_ov)

    def test_metadata_sentence_count(self):
        chunks = SentenceChunker().split(SAMPLE_PT_TEXT)
        for c in chunks:
            assert "sentence_count" in c.metadata
            assert c.metadata["sentence_count"] >= 1

    def test_single_sentence_text(self):
        text = "Uma única frase de teste."
        chunks = SentenceChunker().split(text)
        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_empty_text_returns_empty(self):
        assert SentenceChunker().split("") == []


# ── SemanticChunker ───────────────────────────────────────────────────────────

class TestSemanticChunker:
    """
    Usa mock do OpenAIEmbedder para evitar chamadas à API em CI.
    Os embeddings simulados criam dois grupos semânticos distintos.
    """

    @pytest.fixture
    def mock_embedder(self):
        """
        Simula dois grupos semânticos: frases 0-3 similares entre si,
        frases 4-7 similares entre si, queda brusca entre índices 3 e 4.
        Embeddings: grupo A = [1,0], grupo B = [0,1]
        """
        vectors_8 = [[1.0, 0.0]] * 4 + [[0.0, 1.0]] * 4

        mock = MagicMock()
        mock.embed.return_value = vectors_8
        mock.dimensions = 2
        return mock

    def test_semantic_groups_detected(self, mock_embedder):
        chunker = SemanticChunker(breakpoint_percentile=50)

        with patch.object(chunker, "_get_embedder", return_value=mock_embedder):
            text = "\n".join([
                "Frase sobre inteligência artificial um.",
                "Frase sobre inteligência artificial dois.",
                "Frase sobre inteligência artificial três.",
                "Frase sobre inteligência artificial quatro.",
                "Frase sobre culinária brasileira um.",
                "Frase sobre culinária brasileira dois.",
                "Frase sobre culinária brasileira três.",
                "Frase sobre culinária brasileira quatro.",
            ])
            chunks = chunker.split(text)

        assert len(chunks) >= 2

    def test_metadata_strategy_name(self, mock_embedder):
        chunker = SemanticChunker()
        with patch.object(chunker, "_get_embedder", return_value=mock_embedder):
            chunks = chunker.split(SAMPLE_PT_TEXT)
        for c in chunks:
            assert c.metadata["strategy"] == ChunkingStrategy.semantic.value

    def test_empty_text_returns_empty(self):
        assert SemanticChunker().split("") == []

    def test_single_sentence_no_api_call(self):
        chunker = SemanticChunker()
        # Uma única frase → retorna direto, sem chamar o embedder
        chunks = chunker.split("Apenas uma frase.")
        assert len(chunks) == 1

    def test_oversized_group_is_subdivided(self, mock_embedder):
        # breakpoint_percentile=0 → nenhuma quebra semântica → 1 grupo grande → fallback
        mock_embedder.embed.return_value = [[1.0, 0.0]] * 20
        chunker = SemanticChunker(max_chunk_size=50, breakpoint_percentile=0)
        with patch.object(chunker, "_get_embedder", return_value=mock_embedder):
            long_text = " ".join(["Frase de teste número um."] * 20)
            chunks = chunker.split(long_text)
        assert all(len(c.content) <= 60 for c in chunks)


# ── StructureAwareChunker ─────────────────────────────────────────────────────

class TestStructureAwareChunker:
    def test_xml_lattes_creates_multiple_chunks(self):
        chunker = StructureAwareChunker()
        chunks = chunker.split(SAMPLE_XML_LATTES)
        assert len(chunks) > 3  # dados-gerais + formação + 2 artigos + 1 livro

    def test_each_artigo_is_separate_chunk(self):
        chunker = StructureAwareChunker()
        chunks = chunker.split(SAMPLE_XML_LATTES)
        artigo_chunks = [
            c for c in chunks
            if c.metadata.get("section_type") == "ARTIGO-PUBLICADO"
        ]
        assert len(artigo_chunks) == 2  # 2 artigos no fixture

    def test_livro_is_separate_chunk(self):
        chunker = StructureAwareChunker()
        chunks = chunker.split(SAMPLE_XML_LATTES)
        livro_chunks = [
            c for c in chunks
            if c.metadata.get("section_type") == "LIVRO-PUBLICADO-OU-ORGANIZADO"
        ]
        assert len(livro_chunks) == 1

    def test_metadata_section_type_present(self):
        chunker = StructureAwareChunker()
        chunks = chunker.split(SAMPLE_XML_LATTES)
        for c in chunks:
            assert "section_type" in c.metadata
            assert c.metadata["strategy"] == ChunkingStrategy.structure_aware.value

    def test_artigo_chunk_contains_titulo(self):
        chunker = StructureAwareChunker()
        chunks = chunker.split(SAMPLE_XML_LATTES)
        artigo_chunks = [
            c for c in chunks
            if c.metadata.get("section_type") == "ARTIGO-PUBLICADO"
        ]
        titles_in_content = [
            c for c in artigo_chunks
            if "Avaliação de Estratégias" in c.content
            or "Embeddings Multilíngues" in c.content
        ]
        assert len(titles_in_content) == 2

    def test_fallback_for_plain_text(self):
        chunker = StructureAwareChunker(fallback_chunk_size=100)
        chunks = chunker.split(SAMPLE_PT_TEXT)
        assert len(chunks) > 0
        for c in chunks:
            assert c.metadata.get("fallback") is True
            assert c.metadata["strategy"] == ChunkingStrategy.structure_aware.value

    def test_fallback_for_invalid_xml(self):
        chunker = StructureAwareChunker()
        chunks = chunker.split("<invalid>não é lattes</invalid>")
        # XML mas não Lattes → fallback
        assert len(chunks) > 0
        assert all(c.metadata.get("fallback") for c in chunks)

    def test_empty_text_returns_empty(self):
        assert StructureAwareChunker().split("") == []

    def test_max_chunk_size_respected(self):
        chunker = StructureAwareChunker(max_chunk_size=200)
        chunks = chunker.split(SAMPLE_XML_LATTES)
        for c in chunks:
            assert len(c.content) <= 200, (
                f"Chunk {c.chunk_index} excede max_chunk_size: {len(c.content)} chars"
            )
