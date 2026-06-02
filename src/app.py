import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from src.api.endpoints import v1_router, v2_router  # noqa: E402
from src.core.config import Config  # noqa: E402
from src.core.database import close_firestore, init_firestore  # noqa: E402
from src.core.security import SecurityHeadersMiddleware  # noqa: E402
from src.utils.logger import setup_logging  # noqa: E402

setup_logging()
logger = logging.getLogger(__name__)
config = Config()


try:
    if not os.getenv("PHOENIX_CLIENT_HEADERS"):
        raise ValueError("PHOENIX_CLIENT_HEADERS not set")
    from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
    from phoenix.otel import register

    tracer_provider = register(project_name="lorenzobot")
    LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)
    logger.info("Phoenix OpenTelemetry instrumentation registered")
except Exception as e:
    logger.warning(f"Phoenix instrumentation skipped: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await init_firestore()
    yield
    await close_firestore()


app = FastAPI(
    title="Lorenzo Maiuri Chatbot API",
    version="2.0.0",
    description="AI chatbot backend for lorenzomaiuri.dev",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(v1_router, prefix="/api/v1", tags=["v1 (deprecated)"])
app.include_router(v2_router, prefix="/api/v2", tags=["v2"])
