import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from contextlib import asynccontextmanager
from fastapi import FastAPI
from db import init_db
from vector_store_router import openai_vector_store_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (if needed)

app = FastAPI(title="OpenAI Vector Store Service", lifespan=lifespan)

# Include the vector store router
app.include_router(openai_vector_store_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("openai_vector_store_service:app", host="0.0.0.0", port=8090, reload=True)
