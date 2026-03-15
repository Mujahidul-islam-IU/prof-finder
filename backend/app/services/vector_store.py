"""
ProfFinder — ChromaDB Vector Store Service
Persistent local vector store for student profiles and paper embeddings.
"""

import chromadb
from app.config import get_settings

_chroma_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Get or create the persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        settings = get_settings()
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _chroma_client


def get_student_collection() -> chromadb.Collection:
    """Get or create the student profiles collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="student_profiles",
        metadata={"hnsw:space": "cosine"},
    )


def get_papers_collection() -> chromadb.Collection:
    """Get or create the professor papers collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="professor_papers",
        metadata={"hnsw:space": "cosine"},
    )


def store_student_vector(
    vector_id: str,
    embedding: list[float],
    metadata: dict,
    document: str,
) -> str:
    """Store a student profile embedding in ChromaDB."""
    collection = get_student_collection()
    collection.upsert(
        ids=[vector_id],
        embeddings=[embedding],
        metadatas=[metadata],
        documents=[document],
    )
    return vector_id


def store_paper_vectors(
    paper_ids: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
    documents: list[str],
) -> None:
    """Store multiple paper embeddings in ChromaDB."""
    if not paper_ids:
        return
    collection = get_papers_collection()
    collection.upsert(
        ids=paper_ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents,
    )


def query_similar_papers(
    query_embedding: list[float],
    n_results: int = 10,
    where_filter: dict | None = None,
) -> dict:
    """Query papers collection for similar papers to a given embedding."""
    collection = get_papers_collection()
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter
    return collection.query(**kwargs)


def compute_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import numpy as np
    a = np.array(vec_a)
    b = np.array(vec_b)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
