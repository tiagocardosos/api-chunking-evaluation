from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import analytics, collections, chunking, dashboard, documents, experiments, rag, search
from core.config import settings
from core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="RAG Chunking Evaluation API",
    description="Avaliação de estratégias de chunking em sistemas RAG para documentos institucionais brasileiros",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(collections.router, prefix="/collections", tags=["collections"])
app.include_router(chunking.router, prefix="/chunking", tags=["chunking"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(rag.router, prefix="/rag", tags=["rag"])
app.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


@app.get("/health")
def health():
    return {"status": "ok"}
