import uuid

from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams

from .clients import llm, qdrant
from .settings import settings

COLLECTION = "legal_chunks"
VECTOR_SIZE = 1536  # text-embedding-3-small
CHUNK_CHARS, OVERLAP = 1500, 200


def ensure_collection() -> None:
    if not qdrant.collection_exists(COLLECTION):
        qdrant.create_collection(COLLECTION, vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE))


def chunk(text: str) -> list[str]:
    text = text.strip()
    step = CHUNK_CHARS - OVERLAP
    return [text[i : i + CHUNK_CHARS] for i in range(0, max(len(text), 1), step)]


def embed(texts: list[str]) -> list[list[float]]:
    r = llm.embeddings.create(model=settings.embed_model, input=texts)
    return [d.embedding for d in r.data]


def _eq(key: str, value: str) -> FieldCondition:
    return FieldCondition(key=key, match=MatchValue(value=value))


def upsert_document(tenant_id: str, document_id: str, text: str, payload: dict) -> int:
    ensure_collection()
    # idempotent re-ingestion: drop the document's previous chunks first
    delete_document(tenant_id, document_id)
    chunks = chunk(text)
    points = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{tenant_id}/{document_id}/{i}")),
            vector=v,
            payload={**payload, "tenant_id": tenant_id, "document_id": document_id, "chunk_index": i, "text": c},
        )
        for i, (c, v) in enumerate(zip(chunks, embed(chunks)))
    ]
    qdrant.upsert(COLLECTION, points=points)
    return len(points)


def _doc_filter(tenant_id: str, document_id: str) -> Filter:
    return Filter(must=[_eq("tenant_id", tenant_id), _eq("document_id", document_id)])


def update_document_payload(tenant_id: str, document_id: str, payload: dict) -> None:
    ensure_collection()
    qdrant.set_payload(COLLECTION, payload=payload, points=_doc_filter(tenant_id, document_id))


def delete_document(tenant_id: str, document_id: str) -> None:
    ensure_collection()
    qdrant.delete(COLLECTION, points_selector=_doc_filter(tenant_id, document_id))


def get_source_path(tenant_id: str, document_id: str) -> str | None:
    ensure_collection()
    points, _ = qdrant.scroll(COLLECTION, scroll_filter=Filter(must=[_eq("tenant_id", tenant_id), _eq("document_id", document_id)]),
                              limit=1, with_payload=["source_path"])
    return points[0].payload["source_path"] if points else None


def search(tenant_id: str, query: str, category: str | None = None, limit: int = 5,
           case_id: str | None = None, document_ids: list[str] | None = None):
    ensure_collection()
    must = [_eq("tenant_id", tenant_id)]
    if category:
        must.append(_eq("category", category))
    if case_id:
        must.append(_eq("case_id", case_id))
    if document_ids:
        must.append(FieldCondition(key="document_id", match=MatchAny(any=document_ids)))
    return qdrant.query_points(COLLECTION, query=embed([query])[0], query_filter=Filter(must=must), limit=limit).points
