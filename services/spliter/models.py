from pydantic import BaseModel, HttpUrl, model_validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class DocumentInfo(BaseModel):
    """Information about a document to be processed"""
    id: str
    createdAt: datetime
    lastModifiedAt: datetime
    mimeType: str


class SplitMethod(str, Enum):
    """Enumeration for different LangChain split methods"""
    RECURSIVE_CHARACTER = "recursive_character"  # Most common, tries to split on different separators
    CHARACTER = "character"  # Simple character-based splitting
    TOKEN = "token"  # Token-based splitting (uses tiktoken)
    MARKDOWN = "markdown"  # Markdown-aware splitting
    HTML = "html"  # HTML-aware splitting
    CODE_PYTHON = "code_python"  # Python code-aware splitting
    CODE_JAVASCRIPT = "code_javascript"  # JavaScript code-aware splitting
    SENTENCE = "sentence"  # Sentence-based splitting
    SEMANTIC = "semantic"  # Semantic splitting (requires embeddings)
    

class DocumentSplitRequest(BaseModel):
    """Request model for splitting documents using URL pattern"""
    # Required documents array - always a list (single document = list with one item)
    documents: List[DocumentInfo]  # List of documents to process
    
    # Required URL pattern
    media_download_url_pattern: str  # Pattern like "https://api.example.com/file/{media_id}"
    
    # Common splitting parameters
    split_method: SplitMethod = SplitMethod.RECURSIVE_CHARACTER
    chunk_size: Optional[int] = 1000  # Chunk size in characters or tokens
    chunk_overlap: Optional[int] = 200  # Overlap between chunks
    document_id_prefix: Optional[str] = None  # Prefix for generated document IDs
    separators: Optional[List[str]] = None  # Custom separators for splitting
    keep_separator: Optional[bool] = True  # Whether to keep separators in chunks
    bearer_token: Optional[str] = None  # Bearer token for authenticated requests
    semantic_similarity_threshold: Optional[float] = 0.75  # Threshold for LangChain SemanticChunker (0.0-1.0)
    
    class Config:
        use_enum_values = True
    
    @model_validator(mode='before')
    @classmethod
    def validate_request(cls, values):
        """Validate that required fields are provided"""
        if isinstance(values, dict):
            documents = values.get('documents')
            media_download_url_pattern = values.get('media_download_url_pattern')
            
            if not media_download_url_pattern:
                raise ValueError("'media_download_url_pattern' is required")
            
            if not documents:
                raise ValueError("'documents' is required and must contain at least one document")
            
            if not isinstance(documents, list) or len(documents) == 0:
                raise ValueError("'documents' must be a non-empty list")
                
        return values


class DocumentSplitResponse(BaseModel):
    """Response model for document split operations"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SplitChunk(BaseModel):
    """Model representing a single split chunk"""
    chunk_id: str
    document_id: str
    text_content: str
    chunk_index: int
    total_chunks: int
    metadata: Optional[Dict[str, Any]] = None 