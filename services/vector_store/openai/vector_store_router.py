from fastapi import APIRouter, HTTPException, BackgroundTasks, Body, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from services.vector_store.openai.vector_store_service import vector_store_service
from services.vector_store.openai.models import SyncRequest
from services.common.decorators import response_formatter

openai_vector_store_router = APIRouter(tags=["openai_vector_store"])


class VectorStoreSearchRequest(BaseModel):
    workspace_id: str
    query: str
    max_num_results: Optional[int] = 20


class DeleteFileRequest(BaseModel):
    workspace_id: str
    file_id: str


class DeleteFileByNameRequest(BaseModel):
    workspace_id: str
    file_name: str


@openai_vector_store_router.post("/sync-files")
@response_formatter
async def sync_files(request: SyncRequest, background_tasks: BackgroundTasks):
    """Sync files to OpenAI vector store in background."""
    background_tasks.add_task(sync_file_background, request)
    return JSONResponse(content={"message": "Sync started in background."}, status_code=200)


async def sync_file_background(request: SyncRequest):
    """Background task for syncing files."""
    try:
        result = await vector_store_service.sync_files(request)
        #return JSONResponse(result)
    except Exception as e:
        print(f"Background sync failed: {str(e)}")



@openai_vector_store_router.get("/{workspace_id}/status")
@response_formatter
async def get_workspace_status(workspace_id: str):
    """Get the status of a vector store by workspace ID."""
    try:
        result = await vector_store_service.get_vector_store_status_by_workspace(workspace_id)
        return JSONResponse(content=result.model_dump(), status_code=200)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@openai_vector_store_router.get("/{workspace_id}/files")
@response_formatter
async def get_workspace_files(workspace_id: str):
    """Get all files in a workspace with detailed information."""
    try:
        result = await vector_store_service.get_workspace_files(workspace_id)
        return JSONResponse(content=result.model_dump(), status_code=200)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@openai_vector_store_router.post("/search")
@response_formatter
async def vector_store_search(request: VectorStoreSearchRequest = Body(...)):
    """Search a vector store for documents matching the query."""
    try:
        result = await vector_store_service.search_vector_store(
            request.workspace_id, 
            request.query, 
            request.max_num_results
        )
        return JSONResponse(content=result, status_code=200)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@openai_vector_store_router.post("/files")
@response_formatter
async def insert_file(
    workspace_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Insert a single file into the vector store."""
    try:
        file_content = await file.read()
        result = await vector_store_service.insert_file(
            workspace_id, 
            file_content, 
            file.filename
        )
        return JSONResponse(content=result.model_dump(), status_code=200)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to insert file: {str(e)}")


@openai_vector_store_router.delete("/files")
@response_formatter
async def delete_file(request: DeleteFileRequest = Body(...)):
    """Delete a file from the vector store."""
    try:
        result = await vector_store_service.delete_file(
            request.workspace_id, 
            request.file_id
        )
        return JSONResponse(content=result.model_dump(), status_code=200)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@openai_vector_store_router.delete("/files/delete-by-name")
@response_formatter
async def delete_file_by_name(request: DeleteFileByNameRequest = Body(...)):
    """Delete a file from the vector store by file name."""
    try:
        result = await vector_store_service.delete_file_by_name(
            request.workspace_id, 
            request.file_name
        )
        return JSONResponse(content=result.model_dump(), status_code=200)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}") 