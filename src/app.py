from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from phoenix.otel import register

# Load environment variables
load_dotenv()

from api.endpoints import router as api_router
from core.security import SecurityHeadersMiddleware
from core.database import connect_to_mongo, close_mongo_connection, Mongo
from core.config import Config
from utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Load configuration
config = Config()

# MongoDB client instance (will be set during lifespan)
mongodb_client_instance = None


# Register OpenTelemetry instrumentation for LlamaIndex
try:
    if not os.getenv("PHOENIX_CLIENT_HEADERS"):
        raise ValueError("PHOENIX_CLIENT_HEADERS environment variable is required")
    tracer_provider = register(project_name="lorenzobot")
    LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)
    logger.info("Phoenix Arize LlamaIndex instrumentation registered successfully.")
except Exception as e:
    logger.error(f"Failed to register Phoenix Arize instrumentation: {e}", exc_info=True)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongodb_client_instance
    mongodb_client_instance = await connect_to_mongo()
    app.state.mongo = Mongo(mongodb_client_instance.chatbot_db)
    yield
    await close_mongo_connection(mongodb_client_instance)

# Initialize FastAPI with lifespan
app = FastAPI(
    title="Lorenzo Maiuri Chatbot API",
    version="2.0.0",
    description="Enhanced chatbot API using LlamaIndex framework",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.port,
        reload=config.env == "development",
        log_level="info"
    )