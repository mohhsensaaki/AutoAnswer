from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from services.common.decorators import response_formatter
from services.workflow.n8n.n8n_service import n8n_service
from services.workflow.n8n.models import (
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowTemplatesResponse,
    ClassifierRequest,
    ClassifierResponse
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


@n8n_router.post("/message", response_model=WorkflowExecuteResponse)
@response_formatter
async def execute_workflow(
    request_data: Dict[str, Any] = Body(...)
):
    """
    Execute a workflow for the given workspace and segment.

    Automatically extracts `workspace` as either 'project_id' or 'workspace',
    and `segment` as either 'project_name' or 'segment' from request_data.

    If the workflow doesn't exist, it will be created from a template workflow
    that has tags matching the workspace, segment, and 'template'.

    Args:
        request_data: The data to pass to the workflow, must include identifiers.
    Returns:
        WorkflowExecuteResponse with execution status and results.
    """
    try:
        workspace = request_data.get("project_id") or request_data.get("workspace")
        segment = request_data.get("project_name") or request_data.get("segment")
        if not workspace or not segment:
            raise HTTPException(
                status_code=400,
                detail="Both workspace (or project_id) and segment (or project_name) must be provided in request_data."
            )
        result = await n8n_service.execute_workflow(workspace, segment, request_data)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        status_code = getattr(e, 'status_code', 400)
        raise HTTPException(status_code=status_code, detail=str(e))


@n8n_router.post("/message/classifier", response_model=ClassifierResponse)
@response_formatter
async def classify_message(request: ClassifierRequest) -> ClassifierResponse:
    """
    Trigger classification of input text against a list of classes (async/fire-and-forget).
    
    Triggers the workflow with tags 'message_classifier' and 'v1'.
    Does not wait for the classification result - returns immediately after triggering.
    
    Args:
        request: ClassifierRequest containing:
            - classes: List of class definitions (name and description)
            - input: The text to classify
            
    Returns:
        ClassifierResponse confirming the workflow was triggered
    """
    try:
        # Convert ClassDefinition objects to dicts for the service
        classes_data = [{"name": c.name, "description": c.description} for c in request.classes]
        result = await n8n_service.classify_message(classes_data, request.input)
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