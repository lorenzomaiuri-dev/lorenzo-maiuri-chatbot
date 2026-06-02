import logging
from typing import Optional

from fastapi import Request
from google.cloud.firestore import AsyncClient

from src.core.config import Config

logger = logging.getLogger(__name__)
config = Config()

_firestore_client: Optional[AsyncClient] = None


async def init_firestore() -> AsyncClient:
    global _firestore_client
    _firestore_client = AsyncClient(project=config.gcp_project_id or None)
    logger.info("Firestore client initialized")
    return _firestore_client


async def close_firestore() -> None:
    global _firestore_client
    if _firestore_client:
        _firestore_client.close()
        _firestore_client = None
        logger.info("Firestore client closed")


def get_firestore_db(request: Request) -> AsyncClient:
    return request.app.state.db
