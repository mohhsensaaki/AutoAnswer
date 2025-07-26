from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from services.common.decorators import response_formatter
from services.workflow.n8n.n8n_service import n8n_service
from services.workflow.n8n.models import (
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowTemplatesResponse
)
from typing import Dict, Any

# Create FastAPI router
n8n_router = APIRouter(
    prefix="/workflow",
    tags=["n8n_workflow"]
)


@n8n_router.post("/{workspace}/{segment}/message", response_model=WorkflowExecuteResponse)
@response_formatter
async def execute_workflow(
    workspace: str,
    segment: str,
    request_data: Dict[str, Any] = Body(...)
):
    """
    Execute a workflow for the given workspace and segment.
    
    If the workflow doesn't exist, it will be created from a template workflow
    that has tags matching the workspace, segment, and 'template'.
    
    Args:
        workspace: The workspace identifier
        segment: The segment identifier  
        request_data: The data to pass to the workflow
        
    Returns:
        WorkflowExecuteResponse with execution status and results
    """
    try:
        result = await n8n_service.execute_workflow(workspace, segment, request_data)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        status_code = getattr(e, 'status_code', 400)
        raise HTTPException(status_code=status_code, detail=str(e))
        

@n8n_router.get("/health")
async def health_check():
    """Health check endpoint for n8n workflow service"""
    try:
        return {
            "status": "healthy", 
            "service": "n8n Workflow Service",
            "base_url": n8n_service.n8n_base_url,
            "env_prefix": n8n_service.env_prefix
        }
    except Exception as e:
        status_code = getattr(e, 'status_code', 500)
        raise HTTPException(status_code=status_code, detail=str(e))