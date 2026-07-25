from __future__ import annotations

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from sqlalchemy import text

from backend.db import get_engine

COLLECTION_NAME = "study_genie_docs"
_embeddings: HuggingFaceEmbeddings | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings


def chunk_documents(documents):
    """
    Splits documents into chunks while preserving metadata.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    chunks = text_splitter.split_documents(documents)
    for index, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_id"] = f"chunk-{index}"
        chunk.metadata["snippet"] = chunk.page_content[:320].strip()
    return chunks


def get_vector_store(pre_delete_collection: bool = False) -> PGVector:
    """
    Returns the shared PDF knowledge-base vector store, backed by pgvector.
    Reuses the app's shared SQLAlchemy engine/connection pool rather than
    opening a new database connection per call.
    """
    return PGVector(
        embeddings=_get_embeddings(),
        collection_name=COLLECTION_NAME,
        connection=get_engine(),
        use_jsonb=True,
        pre_delete_collection=pre_delete_collection,
    )


def create_vector_store(chunks) -> PGVector:
    """
    Rebuilds the shared knowledge-base collection from the given chunks,
    replacing whatever was previously ingested (matches the old
    "wipe and recreate on every /rag/ingest call" behavior).
    """
    vectorstore = get_vector_store(pre_delete_collection=True)
    vectorstore.add_documents(chunks)
    return vectorstore


def count_documents() -> int:
    """
    Returns how many chunks are stored in the shared knowledge-base collection.
    Returns 0 if nothing has ever been ingested (the underlying tables may not
    exist yet on a fresh database).
    """
    try:
        with get_engine().connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT count(*)
                    FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                    WHERE c.name = :collection_name
                    """
                ),
                {"collection_name": COLLECTION_NAME},
            ).scalar_one_or_none()
        return int(result or 0)
    except Exception:
        return 0
