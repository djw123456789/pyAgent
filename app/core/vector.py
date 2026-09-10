from qdrant_client import QdrantClient, models

from app.core.config import settings

qdrant_client = QdrantClient(
    url=settings.QDRANT_URL,
)

def ensure_collection() -> None:
    if qdrant_client.collection_exists(settings.QDRANT_COLLECTION):
        return

    qdrant_client.create_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config=models.VectorParams(
            size=qdrant_client.get_embedding_size(
                settings.EMBEDDING_MODEL
            ),
            distance=models.Distance.COSINE,
        ),
    )