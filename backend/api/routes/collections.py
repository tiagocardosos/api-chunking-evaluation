from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.vector_store import VectorStore
from models.db import Collection
from models.schemas import CollectionCreate, CollectionResponse

router = APIRouter()


def get_vector_store() -> VectorStore:
    return VectorStore()


@router.get("", response_model=list[CollectionResponse])
def list_collections(db: Session = Depends(get_db)):
    """Lista todas as coleções cadastradas."""
    return db.query(Collection).order_by(Collection.created_at.desc()).all()


@router.post("", response_model=CollectionResponse, status_code=201)
def create_collection(
    body: CollectionCreate,
    db: Session = Depends(get_db),
):
    """
    Cria uma nova coleção.

    A coleção no Qdrant é criada lazily durante o primeiro ingest.
    Aqui apenas registramos o metadado no PostgreSQL.
    """
    existing = db.query(Collection).filter(Collection.name == body.name).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Coleção {body.name!r} já existe (id={existing.id}).",
        )

    collection = Collection(name=body.name, description=body.description)
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(collection_id: str, db: Session = Depends(get_db)):
    """Retorna metadados de uma coleção pelo ID."""
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Coleção não encontrada.")
    return collection


@router.delete("/{collection_id}", status_code=204)
def delete_collection(
    collection_id: str,
    db: Session = Depends(get_db),
    vs: VectorStore = Depends(get_vector_store),
):
    """
    Remove a coleção do PostgreSQL e do Qdrant.

    Atenção: remove todos os documentos e chunks indexados.
    """
    collection = db.get(Collection, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Coleção não encontrada.")

    if vs.collection_exists(collection_id):
        vs.delete_collection(collection_id)

    db.delete(collection)
    db.commit()
