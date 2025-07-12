import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),'..', '..' , '..', '..','..'))

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from services.common.decorators import response_formatter
from services.vector_store.milvus.milvus_document.document_service import DocumentMilvusService
from services.vector_store.milvus.milvus_document.models import (
    DocumentSaveRequest, 
    DocumentSearchRequest, 
    DocumentVectorSearchRequest,
    DocumentDeleteRequest,
    DocumentCountRequest,
    DocumentResponse
)
import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in the same directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Create global service instance
document_service = DocumentMilvusService(
    uri=os.getenv("MILVUS_URI", "http://localhost:19530/"),
    collection_name=os.getenv("COLLECTION_NAME", "documents")
)

# Create FastAPI app
milvus_document_router = APIRouter(
    prefix="/v1"
)

@milvus_document_router.post("", response_model=DocumentResponse)
@response_formatter
async def save_document(request: DocumentSaveRequest):
    """Save a document to the Milvus collection"""
    try:
        document_service.logger.info(f"Saving document with ID: {request.document_id}")
        
        result = await document_service.save_document(
            document_id=request.document_id,
            text_content=request.text_content
        )
        
        if result.get("success", False):
            return JSONResponse(content=DocumentResponse(
                success=True,
                message="Document saved successfully",
                data=result
            ).model_dump())
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to save document"))
            
    except Exception as e:
        document_service.logger.error(f"Error saving document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@milvus_document_router.post("/search", response_model=DocumentResponse)
@response_formatter
async def search_documents(request: DocumentSearchRequest):
    """Search documents by text query"""
    try:
        document_service.logger.info(f"Searching documents with query: {request.query[:100]}...")
        
        result = await document_service.search_documents_by_text(
            query=request.query,
            limit=request.limit,
            output_fields=request.output_fields
        )
        
        if result.get("success", False):
            return JSONResponse(content=DocumentResponse(
                success=True,
                message=f"Found {result.get('count', 0)} documents",
                data=result
            ).model_dump())
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Search failed"))
            
    except Exception as e:
        document_service.logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@milvus_document_router.post("/search-vector", response_model=DocumentResponse)
@response_formatter
async def search_documents_by_vector(request: DocumentVectorSearchRequest):
    """Search documents by vector similarity"""
    try:
        document_service.logger.info(f"Searching documents with vector similarity, limit: {request.limit}")
        
        result = await document_service.search_documents_by_vector(
            query_vector=request.query_vector,
            limit=request.limit,
            output_fields=request.output_fields
        )
        
        if result.get("success", False):
            return JSONResponse(content=DocumentResponse(
                success=True,
                message=f"Found {result.get('count', 0)} similar documents",
                data=result
            ).model_dump())
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Vector search failed"))
            
    except Exception as e:
        document_service.logger.error(f"Error in vector search: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@milvus_document_router.delete("", response_model=DocumentResponse)
@response_formatter
async def delete_documents(request: DocumentDeleteRequest):
    """Delete documents based on filter expression"""
    try:
        document_service.logger.info(f"Deleting documents with filter: {request.filter_expression}")
        
        result = document_service.delete_documents(request.filter_expression)
        
        if result.get("success", False):
            return JSONResponse(content=DocumentResponse(
                success=True,
                message="Documents deleted successfully",
                data=result
            ).model_dump())
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Delete operation failed"))
            
    except Exception as e:
        document_service.logger.error(f"Error deleting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@milvus_document_router.post("/count", response_model=DocumentResponse)
@response_formatter
async def count_documents(request: DocumentCountRequest):
    """Count documents in the collection"""
    try:
        document_service.logger.info(f"Counting documents with filter: {request.filter_expression}")
        
        result = document_service.count_documents(request.filter_expression)
        
        if result.get("success", False):
            return JSONResponse(content=DocumentResponse(
                success=True,
                message=f"Count completed",
                data=result
            ).model_dump())
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Count operation failed"))
            
    except Exception as e:
        document_service.logger.error(f"Error counting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@milvus_document_router.get("/info", response_model=DocumentResponse)
@response_formatter
async def get_collection_info():
    """Get information about the documents collection"""
    try:
        document_service.logger.info("Getting collection information")
        
        result = document_service.get_documents_info()
        
        return JSONResponse(content=DocumentResponse(
            success=True,
            message="Collection info retrieved successfully",
            data=result
        ).model_dump())
        
    except Exception as e:
        document_service.logger.error(f"Error getting collection info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@milvus_document_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Document Milvus Service"}


# Example usage and testing
if __name__ == "__main__":
    import uvicorn
    
    # Test the service
    document_service.logger.info("Starting Document Milvus Service")
    
    # Run the FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8005) 