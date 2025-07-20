"""
FastAPI application initialization and configuration.
"""
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from services.common.log_creator import create_logger
from services.vector_store.openai.vector_store_router import openai_vector_store_router
from services.vector_store.openai.db import init_db as openai_vector_store_db_init
from services.workflow.n8n.n8n_router import n8n_router
#from config import settings

# Load environment variables from .env file
load_dotenv()

logger = create_logger(is_production=os.getenv("IS_PRODUCTION", "no"), log_url=os.getenv("LOG_URL", "."))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    logger.info("Starting up chatbot platform...")
    openai_vector_store_db_init()
    # Initialize core services here
    # await initialize_vector_db()
    # await initialize_llm_engine()
    
    yield
    
    logger.info("Shutting down chatbot platform...")
    # Clean up resources here


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title="Chatbot Platform API",
        description="A modular chatbot platform supporting multiple business verticals",
        version="0.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(openai_vector_store_router, prefix="/api/v1/vector_store")
    app.include_router(n8n_router, prefix="/api/v1")
    
    return app


app = create_app()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Chatbot platform is running"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 