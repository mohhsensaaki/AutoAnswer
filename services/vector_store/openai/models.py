from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class DocumentMeta(BaseModel):
    id: str
    createdAt: str
    lastModifiedAt: str
    mimeType: str

class SyncRequest(BaseModel):
    workspace_id: str
    documents: List[DocumentMeta]
    media_download_url_pattern: str
    bearer_token: Optional[str] = ''

# Response Models
class FileInfo(BaseModel):
    file_id: str
    status: str
    created_at: int
    filename: Optional[str] = None
    bytes: Optional[int] = None
    purpose: Optional[str] = None

class SyncFilesResponse(BaseModel):
    vector_store_id: str
    synced_documents: List[str]
    uploaded_file_ids: List[str]

class VectorStoreInfoResponse(BaseModel):
    vector_store_id: str
    files: List[FileInfo]

class StatusBreakdown(BaseModel):
    in_progress: int
    completed: int
    failed: int
    cancelled: int

class VectorStoreStatusResponse(BaseModel):
    vector_store_id: str
    workspace_id: str
    overall_status: str
    total_files: int
    status_breakdown: Optional[StatusBreakdown] = None
    files: Optional[List[FileInfo]] = None
    created_at: int
    file_counts: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    response: str

class FileOperationResponse(BaseModel):
    vector_store_id: str
    file_id: str
    status: str
    file_name: Optional[str] = None

class WorkspaceFilesResponse(BaseModel):
    workspace_id: str
    vector_store_id: str
    total_files: int
    files: List[FileInfo]
