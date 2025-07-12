from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class DocumentSaveRequest(BaseModel):
    """Request model for saving a document"""
    document_id: str
    text_content: str


class DocumentSearchRequest(BaseModel):
    """Request model for searching documents"""
    query: str
    limit: Optional[int] = 10
    output_fields: Optional[List[str]] = None


class DocumentVectorSearchRequest(BaseModel):
    """Request model for vector-based document search"""
    query_vector: List[float]
    limit: Optional[int] = 10
    output_fields: Optional[List[str]] = None


class DocumentDeleteRequest(BaseModel):
    """Request model for deleting documents"""
    filter_expression: str


class DocumentCountRequest(BaseModel):
    """Request model for counting documents"""
    filter_expression: Optional[str] = None


class DocumentResponse(BaseModel):
    """Response model for document operations"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None 