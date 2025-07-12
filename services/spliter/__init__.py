"""
Content Splitter Service Package

This package provides functionality for downloading content from URLs,
splitting it into chunks, and saving the chunks to a Milvus vector database.

Main components:
- ContentSplitterService: Core service for downloading and splitting content
- splitter_router: FastAPI router with HTTP endpoints
- models: Pydantic models for requests and responses
"""

from .splitter_service import ContentSplitterService
from .models import (
    DocumentSplitRequest, 
    DocumentSplitResponse, 
    SplitChunk, 
    SplitMethod
)

__all__ = [
    "ContentSplitterService",
    "DocumentSplitRequest",
    "DocumentSplitResponse", 
    "SplitChunk",
    "SplitMethod"
] 