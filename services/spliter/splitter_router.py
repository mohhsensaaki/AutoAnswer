import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from services.common.decorators import response_formatter
from services.spliter.splitter_service import ContentSplitterService
from services.spliter.models import DocumentSplitRequest, DocumentSplitResponse
from services.vector_store.milvus.milvus_document.document_service import DocumentMilvusService
import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in the same directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Create Milvus service instance for saving split documents
milvus_service = DocumentMilvusService(
    uri=os.getenv("MILVUS_URI", "http://localhost:19530/"),
    collection_name=os.getenv("COLLECTION_NAME", "documents")
)

# Create splitter service instance
splitter_service = ContentSplitterService(milvus_service=milvus_service)

# Create FastAPI router
splitter_router = APIRouter(
    prefix="/v1", tags= ["splitter"]
)


@splitter_router.post("/split-url", response_model=DocumentSplitResponse)
@response_formatter
async def split_url_content(request: DocumentSplitRequest):
    """Download content using URL pattern and split it, then save to Milvus"""
    try:
        splitter_service.logger.info(f"Processing document split request: {len(request.documents)} documents")
        
        # Convert Pydantic models to dicts
        documents_dict = [doc.model_dump() for doc in request.documents]
        
        result = await splitter_service.process_documents_and_split(
            documents=documents_dict,
            media_download_url_pattern=request.media_download_url_pattern,
            split_method=request.split_method,
            chunk_size=request.chunk_size or 1000,
            chunk_overlap=request.chunk_overlap or 200,
            document_id_prefix=request.document_id_prefix,
            separators=request.separators,
            keep_separator=request.keep_separator,
            bearer_token=request.bearer_token,
            similarity_threshold=request.semantic_similarity_threshold or 0.75,
            save_to_milvus=True
        )
        
        if result.get("success", False):
            return JSONResponse(content=DocumentSplitResponse(
                success=True,
                message=result.get("message", "Content split and saved successfully"),
                data=result.get("data")
            ).model_dump())
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to split content"))
            
    except Exception as e:
        splitter_service.logger.error(f"Error processing split request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@splitter_router.post("/split-url-preview", response_model=DocumentSplitResponse)
@response_formatter
async def split_url_content_preview(request: DocumentSplitRequest):
    """Download content using URL pattern and split it (preview only - no saving to Milvus)"""
    try:
        splitter_service.logger.info(f"Processing document split preview: {len(request.documents)} documents")
        
        # Convert Pydantic models to dicts
        documents_dict = [doc.model_dump() for doc in request.documents]
        
        result = await splitter_service.process_documents_and_split(
            documents=documents_dict,
            media_download_url_pattern=request.media_download_url_pattern,
            split_method=request.split_method,
            chunk_size=request.chunk_size or 1000,
            chunk_overlap=request.chunk_overlap or 200,
            document_id_prefix=request.document_id_prefix,
            separators=request.separators,
            keep_separator=request.keep_separator,
            bearer_token=request.bearer_token,
            similarity_threshold=request.semantic_similarity_threshold or 0.75,
            save_to_milvus=False  # Preview mode - don't save
        )
        
        if result.get("success", False):
            processed = result['data']['processed_documents']
            total = result['data']['total_documents']
            chunks = result['data']['total_chunks']
            message = f"Document split preview completed - {processed}/{total} documents processed, {chunks} chunks generated"
            
            return JSONResponse(content=DocumentSplitResponse(
                success=True,
                message=message,
                data=result.get("data")
            ).model_dump())
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to split content"))
            
    except Exception as e:
        splitter_service.logger.error(f"Error processing split preview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@splitter_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "Content Splitter Service",
        "milvus_connected": milvus_service is not None
    }


@splitter_router.get("/info")
@response_formatter
async def get_service_info():
    """Get information about the splitter service"""
    try:
        # Get Milvus collection info if available
        milvus_info = None
        if milvus_service:
            milvus_info = milvus_service.get_documents_info()
        
        service_info = {
            "service_name": "Content Splitter Service (LangChain-powered)",
            "version": "2.0.0",
            "langchain_version": "0.1.0",
            "supported_split_methods": [
                "recursive_character", "character", "token", "markdown", 
                "html", "code_python", "code_javascript", "sentence", "semantic"
            ],
            "method_descriptions": {
                "recursive_character": "Most versatile, tries multiple separators hierarchically",
                "character": "Simple splitting by single separator", 
                "token": "Token-based splitting using tiktoken (GPT-4 encoding)",
                "markdown": "Markdown-aware splitting preserving structure",
                "html": "HTML-aware splitting by headers and structure",
                "code_python": "Python code-aware splitting",
                "code_javascript": "JavaScript code-aware splitting",
                "sentence": "Sentence-boundary aware splitting",
                "semantic": "LangChain SemanticChunker with percentile-based breakpoint detection"
            },
            "supported_content_types": [
                "application/json", 
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword"
            ],
            "supported_file_extensions": [
                "json", "pdf", "docx", "doc"
            ],
            "features": [
                "Configurable chunk size and overlap",
                "Custom separators support", 
                "Separator preservation options",
                "Bearer token authentication for protected URLs",
                "LangChain SemanticChunker with statistical breakpoint detection",
                "Configurable percentile threshold for semantic splitting",
                "PDF processing with PyPDFLoader and PDFPlumberLoader fallback",
                "DOCX processing with Docx2txtLoader and UnstructuredWordDocumentLoader",
                "JSON processing with LangChain JSONLoader",
                "Multi-document batch processing with media download URL patterns",
                "File type validation (PDF, DOCX, JSON only)",
                "Support for both single URL and document list modes",
                "Comprehensive error handling and progress tracking",
                "Robust fallback mechanisms",
                "Preview mode"
            ],
            "milvus_service": {
                "connected": milvus_service is not None,
                "collection_info": milvus_info
            }
        }
        
        return JSONResponse(content=DocumentSplitResponse(
            success=True,
            message="Service info retrieved successfully",
            data=service_info
        ).model_dump())
        
    except Exception as e:
        splitter_service.logger.error(f"Error getting service info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Example usage and testing
if __name__ == "__main__":
    import uvicorn
    
    # Test the service
    splitter_service.logger.info("Starting Content Splitter Service")
    
    # Run the FastAPI app
    from fastapi import FastAPI
    app = FastAPI(title="Content Splitter Service")
    app.include_router(splitter_router, prefix="/splitter")
    
    uvicorn.run(app, host="0.0.0.0", port=8001) 