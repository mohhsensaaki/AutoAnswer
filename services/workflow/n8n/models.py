from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class WorkflowExecuteRequest(BaseModel):
    """Request model for executing a workflow"""
    # This will accept any fields in the body since n8n workflows can have various inputs
    data: Dict[str, Any]
    status_code: Optional[int] = None


class WorkflowTemplateInfo(BaseModel):
    """Model for workflow template information"""
    id: str
    name: str
    description: Optional[str] = None
    workspace: Optional[str] = None
    tags: Optional[List[str]] = None
    status_code: Optional[int] = None


class WorkflowTemplatesResponse(BaseModel):
    """Response model for listing workflow templates"""
    success: bool
    templates: List[WorkflowTemplateInfo]
    message: Optional[str] = None
    status_code: Optional[int] = None


class WorkflowExecuteResponse(BaseModel):
    """Response model for workflow execution"""
    success: bool
    message: Optional[str] = None
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


class N8nWorkflowCloneRequest(BaseModel):
    """Internal model for cloning workflow requests to n8n API"""
    name: str
    tags: Optional[List[str]] = None
    status_code: Optional[int] = None


class N8nWorkflowUpdateRequest(BaseModel):
    """Internal model for updating workflow trigger URL"""
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    settings: Optional[Dict[str, Any]] = None
    status_code: Optional[int] = None