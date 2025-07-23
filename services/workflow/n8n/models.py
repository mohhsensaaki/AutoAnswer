from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class WorkflowExecuteRequest(BaseModel):
    """Request model for executing a workflow"""
    # This will accept any fields in the body since n8n workflows can have various inputs
    data: Dict[str, Any]



class WorkflowTemplatesResponse(BaseModel):
    """Response model for listing workflow templates"""
    templates: List[str]
    message: Optional[str] = None


class WorkflowExecuteResponse(BaseModel):
    """Response model for workflow execution"""
    message: Optional[str] = None


class N8nWorkflowCloneRequest(BaseModel):
    """Internal model for cloning workflow requests to n8n API"""
    name: str
    tags: Optional[List[str]] = None


class N8nWorkflowUpdateRequest(BaseModel):
    """Internal model for updating workflow trigger URL"""
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    settings: Optional[Dict[str, Any]] = None