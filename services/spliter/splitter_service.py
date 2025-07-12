import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import httpx
import uuid
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from datetime import datetime
from services.common.log_creator import create_logger
from services.spliter.models import SplitMethod, SplitChunk, DocumentInfo
from services.vector_store.milvus.milvus_document.document_service import DocumentMilvusService
from services.embedding.openai.embedding_service import create_embeddings
from services.embedding.openai.models import Item

# LangChain imports
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
    TokenTextSplitter,
    MarkdownTextSplitter,
    HTMLHeaderTextSplitter,
    PythonCodeTextSplitter,
    RecursiveCharacterTextSplitter,
    SentenceTransformersTokenTextSplitter
)
from langchain.text_splitter import Language
from langchain_experimental.text_splitter import SemanticChunker
from langchain.embeddings.base import Embeddings
from langchain_community.document_loaders import (
    PyPDFLoader,
    PDFPlumberLoader,
    Docx2txtLoader,
    UnstructuredWordDocumentLoader,
    JSONLoader
)
import tiktoken
import numpy as np
import tempfile
import json
import mimetypes


class CustomEmbeddings(Embeddings):
    """Custom embeddings class that interfaces with our embedding service"""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents synchronously"""
        import asyncio
        return asyncio.run(self.aembed_documents(texts))
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents asynchronously"""
        try:
            embeddings_list = []
            
            # Process texts in batches
            batch_size = 10
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_contents = [{"text": text} for text in batch]
                
                try:
                    embedding_result = await create_embeddings(
                        Item(contents=batch_contents, features=["text"])
                    )
                    
                    for result in embedding_result:
                        if "embedding" in result:
                            embeddings_list.append(result["embedding"])
                        else:
                            # Fallback: use zero vector if embedding fails
                            embeddings_list.append([0.0] * 1536)
                            
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Error getting embeddings for batch {i//batch_size + 1}: {e}")
                    # Add zero vectors for failed batch
                    for _ in batch:
                        embeddings_list.append([0.0] * 1536)
            
            return embeddings_list
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in aembed_documents: {str(e)}")
            # Return zero vectors as fallback
            return [[0.0] * 1536 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query synchronously"""
        import asyncio
        return asyncio.run(self.aembed_query(text))
    
    async def aembed_query(self, text: str) -> List[float]:
        """Embed a single query asynchronously"""
        embeddings = await self.aembed_documents([text])
        return embeddings[0] if embeddings else [0.0] * 1536


class ContentSplitterService:
    """Service for downloading content from URLs and splitting it into chunks"""
    
    def __init__(self, milvus_service: DocumentMilvusService = None, logger=None):
        """Initialize Content Splitter Service"""
        if logger is None:
            is_production = os.getenv("IS_PRODUCTION", "no")
            log_url = os.getenv("LOG_URL", ".")
            self.logger = create_logger(is_production, log_url)
        else:
            self.logger = logger
            
        self.milvus_service = milvus_service
        self.timeout = httpx.Timeout(30.0)  # 30 seconds timeout
        
        # Initialize custom embeddings for semantic splitting
        self.embeddings = CustomEmbeddings(logger=self.logger)
    
    async def download_content(self, url: str, bearer_token: Optional[str] = None) -> str:
        """Download content from URL with optional bearer token authentication and file type detection"""
        try:
            self.logger.info(f"Downloading content from: {url}")
            
            # Prepare headers
            headers = {}
            if bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"
                self.logger.info("Using bearer token authentication")
            
            async with httpx.AsyncClient(timeout=999999999999) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                # Get content type and detect file type
                content_type = response.headers.get('content-type', '').lower()
                
                # Detect file type from URL extension as backup
                url_extension = url.lower().split('.')[-1].split('?')[0]  # Handle query params
                
                self.logger.info(f"Content type: {content_type}, URL extension: {url_extension}")
                
                # Store detected MIME type for single document mode
                detected_mime_type = None
                
                # Handle only supported file types: PDF, DOCX, JSON
                if 'application/pdf' in content_type or url_extension == 'pdf':
                    detected_mime_type = 'application/pdf'
                    content = await self.process_pdf_content(response.content, url)
                
                elif ('application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type or 
                      'application/msword' in content_type or 
                      url_extension in ['docx', 'doc']):
                    if 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                        detected_mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    else:
                        detected_mime_type = 'application/msword'
                    content = await self.process_docx_content(response.content, url)
                
                elif 'application/json' in content_type or url_extension == 'json':
                    detected_mime_type = 'application/json'
                    content = await self.process_json_content(response.text, url)
                
                else:
                    # Reject unsupported file types
                    raise Exception(f"Unsupported content type: {content_type}. Only PDF, DOCX, and JSON files are supported.")
                
                # Store the detected MIME type for later use
                self._last_detected_mime_type = detected_mime_type
                
                self.logger.info(f"Successfully processed {len(content)} characters from {url}")
                return content
                
        except Exception as e:
            error_msg = f"Error downloading/processing content from {url}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    async def process_pdf_content(self, pdf_bytes: bytes, url: str) -> str:
        """Process PDF content using LangChain PDF loaders"""
        try:
            self.logger.info("Processing PDF content using LangChain loaders")
            
            # Create temporary file for PDF processing
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(pdf_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Try PyPDFLoader first (faster)
                loader = PyPDFLoader(temp_file_path)
                documents = loader.load()
                
                if not documents:
                    # Fallback to PDFPlumberLoader (more accurate for complex PDFs)
                    self.logger.info("PyPDFLoader returned no content, trying PDFPlumberLoader")
                    loader = PDFPlumberLoader(temp_file_path)
                    documents = loader.load()
                
                # Combine all pages into single text
                content = "\n\n".join([doc.page_content for doc in documents])
                
                if not content.strip():
                    raise Exception("No text content could be extracted from PDF")
                
                self.logger.info(f"Successfully extracted {len(content)} characters from PDF")
                return content
                
            finally:
                # Clean up temporary file
                import os
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
        except Exception as e:
            error_msg = f"Error processing PDF content: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    async def process_docx_content(self, docx_bytes: bytes, url: str) -> str:
        """Process DOCX content using LangChain DOCX loaders"""
        try:
            self.logger.info("Processing DOCX content using LangChain loaders")
            
            # Create temporary file for DOCX processing
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
                temp_file.write(docx_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Try Docx2txtLoader first (simpler and faster)
                try:
                    loader = Docx2txtLoader(temp_file_path)
                    documents = loader.load()
                    content = "\n\n".join([doc.page_content for doc in documents])
                except Exception as e:
                    self.logger.info(f"Docx2txtLoader failed: {e}, trying UnstructuredWordDocumentLoader")
                    # Fallback to UnstructuredWordDocumentLoader
                    loader = UnstructuredWordDocumentLoader(temp_file_path)
                    documents = loader.load()
                    content = "\n\n".join([doc.page_content for doc in documents])
                
                if not content.strip():
                    raise Exception("No text content could be extracted from DOCX")
                
                self.logger.info(f"Successfully extracted {len(content)} characters from DOCX")
                return content
                
            finally:
                # Clean up temporary file
                import os
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
        except Exception as e:
            error_msg = f"Error processing DOCX content: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    async def process_json_content(self, json_text: str, url: str) -> str:
        """Process JSON content using LangChain JSON loader"""
        try:
            self.logger.info("Processing JSON content using LangChain JSONLoader")
            
            # Create temporary file for JSON processing
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(json_text)
                temp_file_path = temp_file.name
            
            try:
                # Use JSONLoader to extract text content
                loader = JSONLoader(
                    file_path=temp_file_path,
                    jq_schema='.',  # Extract all content
                    text_content=False  # Don't expect specific text field
                )
                documents = loader.load()
                
                if documents:
                    content = "\n\n".join([doc.page_content for doc in documents])
                else:
                    # Fallback: pretty-format the JSON as text
                    try:
                        parsed_json = json.loads(json_text)
                        content = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                    except json.JSONDecodeError:
                        content = json_text
                
                self.logger.info(f"Successfully processed {len(content)} characters from JSON")
                return content
                
            finally:
                # Clean up temporary file
                import os
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
        except Exception as e:
            error_msg = f"Error processing JSON content: {str(e)}"
            self.logger.error(error_msg)
            # Fallback to raw JSON text
            self.logger.warning("Falling back to raw JSON text")
            return json_text
    
    def construct_download_url(self, media_id: str, url_pattern: str) -> str:
        """Construct download URL from pattern and media ID"""
        return url_pattern.replace("{media_id}", media_id)
    
    async def download_and_process_document(self, doc_info: dict, url_pattern: str, bearer_token: Optional[str] = None) -> dict:
        """Download and process a single document"""
        try:
            doc_id = doc_info["id"]
            mime_type = doc_info.get("mimeType", "unknown")
            
            # Construct download URL
            download_url = self.construct_download_url(doc_id, url_pattern)
            
            self.logger.info(f"Processing document {doc_id} ({mime_type}) from {download_url}")
            
            # If mime type is unknown, detect it during download
            if mime_type == "unknown":
                self.logger.info("MIME type unknown, will detect from content-type header")
                content = await self.download_content(download_url, bearer_token)
                # Get the actual mime type from the response (this will be set by download_content)
                mime_type = getattr(self, '_last_detected_mime_type', 'unknown')
            else:
                # Validate supported file types first
                if not (mime_type in ['application/pdf', 'application/json', 
                                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                     'application/msword'] or
                       mime_type.startswith('application/pdf') or
                       mime_type.startswith('application/json')):
                    raise Exception(f"Unsupported file type: {mime_type}. Only PDF, DOCX, and JSON files are supported.")
                
                # Download and process supported file types
                content = await self.download_content(download_url, bearer_token)
            
            return {
                "document_id": doc_id,
                "mime_type": mime_type,
                "download_url": download_url,
                "content": content,
                "success": True,
                "content_length": len(content)
            }
            
        except Exception as e:
            error_msg = f"Error processing document {doc_info.get('id', 'unknown')}: {str(e)}"
            self.logger.error(error_msg)
            return {
                "document_id": doc_info.get("id", "unknown"),
                "mime_type": doc_info.get("mimeType", "unknown"),
                "download_url": download_url if 'download_url' in locals() else "unknown",
                "content": "",
                "success": False,
                "error": str(e),
                "content_length": 0
            }
    
    def create_langchain_splitter(
        self, 
        split_method: SplitMethod, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        similarity_threshold: float = 0.75
    ):
        """Create appropriate LangChain text splitter based on method"""
        
        if split_method == SplitMethod.RECURSIVE_CHARACTER:
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=separators or ["\n\n", "\n", " ", ""],
                keep_separator=keep_separator
            )
        
        elif split_method == SplitMethod.CHARACTER:
            return CharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separator=separators[0] if separators else "\n\n",
                keep_separator=keep_separator
            )
        
        elif split_method == SplitMethod.TOKEN:
            return TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                encoding_name="cl100k_base"  # GPT-4 encoding
            )
        
        elif split_method == SplitMethod.MARKDOWN:
            return MarkdownTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        
        elif split_method == SplitMethod.HTML:
            headers_to_split_on = [
                ("h1", "Header 1"),
                ("h2", "Header 2"),
                ("h3", "Header 3"),
                ("h4", "Header 4"),
                ("h5", "Header 5"),
                ("h6", "Header 6"),
            ]
            html_splitter = HTMLHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            # For HTML, we use a two-step process
            return html_splitter
        
        elif split_method == SplitMethod.CODE_PYTHON:
            return RecursiveCharacterTextSplitter.from_language(
                language=Language.PYTHON,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        
        elif split_method == SplitMethod.CODE_JAVASCRIPT:
            return RecursiveCharacterTextSplitter.from_language(
                language=Language.JS,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        
        elif split_method == SplitMethod.SENTENCE:
            # Use RecursiveCharacterTextSplitter with sentence-friendly separators
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=[". ", "! ", "? ", "\n\n", "\n", " ", ""],
                keep_separator=True
            )
        
        elif split_method == SplitMethod.SEMANTIC:
            # Use LangChain's SemanticChunker
            return SemanticChunker(
                embeddings=self.embeddings,
                breakpoint_threshold_type="percentile",  # or "standard_deviation", "interquartile"
                breakpoint_threshold_amount=similarity_threshold or 0.75
            )
        
        else:
            raise ValueError(f"Unknown split method: {split_method}")
    
    def split_html_content(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """Special handling for HTML content"""
        try:
            # First pass: HTML header splitting
            headers_to_split_on = [
                ("h1", "Header 1"),
                ("h2", "Header 2"), 
                ("h3", "Header 3"),
                ("h4", "Header 4"),
                ("h5", "Header 5"),
                ("h6", "Header 6"),
            ]
            html_splitter = HTMLHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            html_header_splits = html_splitter.split_text(text)
            
            # Second pass: Character splitting for large sections
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            final_chunks = []
            for doc in html_header_splits:
                if len(doc.page_content) > chunk_size:
                    sub_chunks = text_splitter.split_text(doc.page_content)
                    final_chunks.extend(sub_chunks)
                else:
                    final_chunks.append(doc.page_content)
            
            return final_chunks
            
        except Exception as e:
            self.logger.warning(f"HTML splitting failed, falling back to recursive character splitting: {e}")
            # Fallback to regular splitting
            fallback_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            return fallback_splitter.split_text(text)
    
    def split_content(
        self, 
        content: str, 
        split_method: SplitMethod, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        similarity_threshold: float = 0.75
    ) -> List[str]:
        """Split content using LangChain text splitters"""
        self.logger.info(f"Splitting content using LangChain method: {split_method}")
        
        try:
            # Special handling for HTML content
            if split_method == SplitMethod.HTML:
                return self.split_html_content(content, chunk_size, chunk_overlap)
            
            # Create appropriate LangChain splitter (including semantic)
            splitter = self.create_langchain_splitter(
                split_method=split_method,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=separators,
                keep_separator=keep_separator,
                similarity_threshold=similarity_threshold
            )
            
            # Split the content
            chunks = splitter.split_text(content)
            
            # Filter out very small chunks (less than 10 characters)
            chunks = [chunk.strip() for chunk in chunks if chunk.strip() and len(chunk.strip()) > 10]
            
            self.logger.info(f"Successfully split content into {len(chunks)} chunks using {split_method}")
            return chunks
            
        except Exception as e:
            error_msg = f"Error splitting content with method {split_method}: {str(e)}"
            self.logger.error(error_msg)
            
            # Fallback to recursive character splitting
            self.logger.warning("Falling back to recursive character splitting")
            fallback_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            return fallback_splitter.split_text(content)
    
    def generate_document_id(self, url: str, chunk_index: int, prefix: Optional[str] = None) -> str:
        """Generate a unique document ID for a chunk"""
        # Parse URL to get domain and path
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('.', '_')
        path = parsed_url.path.replace('/', '_').replace('.', '_')
        
        # Create base ID
        base_id = f"{domain}{path}"
        if prefix:
            base_id = f"{prefix}_{base_id}"
        
        # Add chunk index and timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = f"{base_id}_chunk_{chunk_index:04d}_{timestamp}"
        
        return document_id
    
    async def process_documents_and_split(
        self,
        documents: List[dict],
        media_download_url_pattern: str,
        split_method: SplitMethod = SplitMethod.RECURSIVE_CHARACTER,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        document_id_prefix: Optional[str] = None,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        bearer_token: Optional[str] = None,
        similarity_threshold: float = 0.75,
        save_to_milvus: bool = True
    ) -> Dict[str, Any]:
        """Process multiple documents from document list"""
        try:
            self.logger.info(f"Processing {len(documents)} documents using pattern: {media_download_url_pattern}")
            
            all_chunks = []
            all_saved_chunks = []
            processed_documents = []
            failed_documents = []
            
            # Process each document
            for doc_info in documents:
                try:
                    # Download and extract content
                    doc_result = await self.download_and_process_document(
                        doc_info, media_download_url_pattern, bearer_token
                    )
                    
                    if not doc_result["success"]:
                        failed_documents.append(doc_result)
                        continue
                    
                    content = doc_result["content"]
                    doc_id = doc_result["document_id"]
                    
                    if not content.strip():
                        self.logger.warning(f"No content extracted from document {doc_id}")
                        failed_documents.append({
                            **doc_result,
                            "error": "No content extracted"
                        })
                        continue
                    
                    # Split content
                    chunks = self.split_content(
                        content=content,
                        split_method=split_method,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        separators=separators,
                        keep_separator=keep_separator,
                        similarity_threshold=similarity_threshold
                    )
                    
                    self.logger.info(f"Split document {doc_id} into {len(chunks)} chunks")
                    
                    # Create chunk objects for this document
                    doc_chunks = []
                    doc_saved_chunks = []
                    
                    for i, chunk_text in enumerate(chunks):
                        # Generate unique document ID for this chunk
                        chunk_doc_id = self.generate_document_id_for_doc(
                            doc_id, i, document_id_prefix, doc_result["mime_type"]
                        )
                        
                        chunk_obj = SplitChunk(
                            chunk_id=str(uuid.uuid4()),
                            document_id=chunk_doc_id,
                            text_content=chunk_text,
                            chunk_index=i,
                            total_chunks=len(chunks),
                            metadata={
                                "source_document_id": doc_id,
                                "source_mime_type": doc_result["mime_type"],
                                "source_download_url": doc_result["download_url"],
                                "split_method": split_method,
                                "chunk_size": chunk_size,
                                "chunk_overlap": chunk_overlap,
                                "created_at": datetime.now().isoformat()
                            }
                        )
                        
                        doc_chunks.append(chunk_obj)
                        all_chunks.append(chunk_obj)
                        
                        # Save to Milvus if requested
                        if save_to_milvus and self.milvus_service:
                            try:
                                result = await self.milvus_service.save_document(
                                    document_id=chunk_doc_id,
                                    text_content=chunk_text
                                )
                                
                                save_result = {
                                    "document_id": chunk_doc_id,
                                    "chunk_index": i,
                                    "source_document_id": doc_id,
                                    "status": "saved" if result.get("success", False) else "failed",
                                }
                                
                                if not result.get("success", False):
                                    save_result["error"] = result.get("error", "Unknown error")
                                
                                doc_saved_chunks.append(save_result)
                                all_saved_chunks.append(save_result)
                                
                            except Exception as e:
                                self.logger.error(f"Error saving chunk {i} of document {doc_id} to Milvus: {str(e)}")
                                save_result = {
                                    "document_id": chunk_doc_id,
                                    "chunk_index": i,
                                    "source_document_id": doc_id,
                                    "status": "failed",
                                    "error": str(e)
                                }
                                doc_saved_chunks.append(save_result)
                                all_saved_chunks.append(save_result)
                    
                    # Record successful document processing
                    processed_documents.append({
                        "document_id": doc_id,
                        "mime_type": doc_result["mime_type"],
                        "content_length": doc_result["content_length"],
                        "chunks_created": len(doc_chunks),
                        "chunks_saved": len([c for c in doc_saved_chunks if c["status"] == "saved"]) if save_to_milvus else None
                    })
                    
                except Exception as e:
                    error_msg = f"Error processing document {doc_info.get('id', 'unknown')}: {str(e)}"
                    self.logger.error(error_msg)
                    failed_documents.append({
                        "document_id": doc_info.get("id", "unknown"),
                        "mime_type": doc_info.get("mimeType", "unknown"),
                        "error": str(e)
                    })
            
            # Prepare response
            response_data = {
                "total_documents": len(documents),
                "processed_documents": len(processed_documents),
                "failed_documents": len(failed_documents),
                "total_chunks": len(all_chunks),
                "split_method": split_method,
                "documents_summary": processed_documents,
                "failed_documents_details": failed_documents if failed_documents else None,
                "chunks": [chunk.model_dump() for chunk in all_chunks]
            }
            
            if save_to_milvus and self.milvus_service:
                successful_saves = len([c for c in all_saved_chunks if c["status"] == "saved"])
                response_data["milvus_saves"] = {
                    "total_attempted": len(all_saved_chunks),
                    "successful": successful_saves,
                    "failed": len(all_saved_chunks) - successful_saves,
                    "details": all_saved_chunks
                }
            
            return {
                "success": True,
                "message": f"Processed {len(processed_documents)} of {len(documents)} documents, created {len(all_chunks)} chunks",
                "data": response_data
            }
            
        except Exception as e:
            error_msg = f"Error processing document list: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": str(e),
                "message": error_msg
            }
    
    def generate_document_id_for_doc(self, source_doc_id: str, chunk_index: int, prefix: Optional[str] = None, mime_type: str = "") -> str:
        """Generate a unique document ID for a chunk from a source document"""
        # Create base ID from source document ID
        base_id = f"doc_{source_doc_id}"
        if prefix:
            base_id = f"{prefix}_{base_id}"
        
        # Add mime type info
        if mime_type:
            mime_short = mime_type.split('/')[-1].replace('-', '_')
            base_id = f"{base_id}_{mime_short}"
        
        # Add chunk index and timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        document_id = f"{base_id}_chunk_{chunk_index:04d}_{timestamp}"
        
        return document_id 