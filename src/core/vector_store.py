import logging
from typing import Optional

import httpx
from google.cloud.firestore import AsyncClient
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector

from src.core.config import Config

logger = logging.getLogger(__name__)
config = Config()

_firestore_client: Optional[AsyncClient] = None


def get_vector_db() -> AsyncClient:
    """Returns a lazily-initialised Firestore AsyncClient for vector operations."""
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = AsyncClient(project=config.gcp_project_id or None)
        logger.info("Firestore vector client initialised")
    return _firestore_client


async def embed_text(text: str) -> list[float]:
    """Calls the Google AI embedding REST endpoint and returns the vector."""
    model = config.gemini_embedding_model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            params={"key": config.gemini_api_key},
            json={"model": f"models/{model}", "content": {"parts": [{"text": text}]}},
        )
        resp.raise_for_status()
    return resp.json()["embedding"]["values"]


async def vector_search(
    collection_name: str,
    query: str,
    n_results: int = 3,
) -> list[dict]:
    """
    Embeds `query` and runs Firestore find_nearest on `collection_name`.
    Returns a list of document dicts (excluding the embedding field).
    Raises RuntimeError if the vector index doesn't exist yet — caller should handle gracefully.
    """
    embedding = await embed_text(query)
    db = get_vector_db()

    results = await (
        db.collection(collection_name)
        .find_nearest(
            vector_field="embedding",
            query_vector=Vector(embedding),
            distance_measure=DistanceMeasure.COSINE,
            limit=n_results,
        )
        .get()
    )

    return [{k: v for k, v in doc.to_dict().items() if k != "embedding"} for doc in results]
