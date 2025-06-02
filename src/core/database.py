from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
import logging
from fastapi import Request

from src.core.config import Config

logger = logging.getLogger(__name__)
config = Config()

# Global client to be managed by lifespan
mongodb_client_instance: AsyncMongoClient

async def connect_to_mongo():
    """Connects to MongoDB and returns the client."""
    global mongodb_client_instance

    try:
        mongodb_client_instance = AsyncMongoClient(config.mongodb_url)
        await mongodb_client_instance.admin.command("ping")
        logger.info("MongoDB connection established")

        # Ensure index on chatId
        await mongodb_client_instance.chatbot_db.sessions.create_index("chatId", unique=True)
        logger.info("MongoDB index on chatId ensured.")

        return mongodb_client_instance
    
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongo_connection(client: AsyncMongoClient):
    """Closes the MongoDB connection."""
    if client:
        await client.close()
        logger.info("MongoDB connection closed")

class Mongo:
    def __init__(self, db: AsyncDatabase):
        self.sessions = db.sessions
    
def get_mongo(request: Request) -> Mongo:
    """FastAPI dependency to inject Mongo instance."""
    return request.app.state.mongo
