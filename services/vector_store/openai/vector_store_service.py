import os

import aiofiles
import httpx
import tempfile
from openai import AsyncOpenAI
from dotenv import load_dotenv
from mimetypes import guess_extension
from services.common.log_creator import create_logger

from services.vector_store.openai.db import get_vector_store_id, set_vector_store_id
from services.vector_store.openai.models import (
    SyncRequest, SyncFilesResponse, VectorStoreInfoResponse, 
    VectorStoreStatusResponse, SearchResponse, FileOperationResponse,
    WorkspaceFilesResponse, FileInfo, StatusBreakdown
)



# Load environment variables
load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_MANAGER_API_KEY = os.getenv("CHANNEL_MANAGER_API_KEY")
IS_PRODUCTION = os.getenv("IS_PRODUCTION", "no")
LOG_URL = os.getenv("LOG_URL", "vector_store_service.log")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set in environment variables.")

if not CHANNEL_MANAGER_API_KEY:
    raise ValueError("CHANNEL_MANAGER_API_KEY must be set in environment variables.")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


class VectorStoreService:
    def __init__(self):
        self.client = client
        self.files_dir = "openai_vector_store/files"
        self.logger = create_logger(IS_PRODUCTION, LOG_URL)

    async def download_file(self, media_id: str, download_url_pattern: str, bearer_token: str, save_path: str):
        """Download a file from the media download URL and save it locally."""
        self.logger.info(f"Starting file download: media_id={media_id}, save_path={save_path}")
        
        download_url = download_url_pattern.replace("{media_id}", media_id)
        headers = {"Authorization": f"Bearer {bearer_token}"}

        try:
            async with httpx.AsyncClient() as client:
                self.logger.debug(f"Making HTTP request to: {download_url}")
                response = await client.get(download_url, headers=headers, timeout=60*10)
                response.raise_for_status()

                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                # Save file
                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(response.content)
                
                self.logger.info(f"Successfully downloaded file: {save_path}")
        except Exception as e:
            self.logger.error(f"Failed to download file {media_id}: {str(e)}")
            raise

    async def get_or_create_vector_store_id(self, workspace_id: str) -> str:
        """Get existing vector store ID or create a new one."""
        self.logger.info(f"Getting or creating vector store for workspace: {workspace_id}")
        
        # Try to get vector_store_id from DB
        vector_store_id = get_vector_store_id(workspace_id)
        if vector_store_id:
            self.logger.info(f"Found existing vector store: {vector_store_id}")
            return vector_store_id
        
        # Create new vector store
        self.logger.info(f"Creating new vector store for workspace: {workspace_id}")
        try:
            vs = await self.client.vector_stores.create(name=workspace_id)
            set_vector_store_id(workspace_id, vs.id)
            self.logger.info(f"Created new vector store: {vs.id}")
            return vs.id
        except Exception as e:
            self.logger.error(f"Failed to create vector store for workspace {workspace_id}: {str(e)}")
            raise

    async def sync_files(self, request: SyncRequest) -> SyncFilesResponse:
        """Sync files to the OpenAI vector store for a workspace."""
        workspace_id = request.workspace_id
        self.logger.info(f"Starting file sync for workspace: {workspace_id}, documents count: {len(request.documents)}")
        
        if not workspace_id:
            self.logger.error("Sync failed: workspace_id is required")
            raise ValueError("workspace_id required")

        # Get or create the vector store
        vector_store_id = await self.get_or_create_vector_store_id(workspace_id)
        
        # Get current documents filenames
        current_doc_filenames = set()
        current_doc_mime_types = dict()
        for doc in request.documents:
            file_name = doc.id + guess_extension(doc.mimeType.strip())
            current_doc_filenames.add(file_name)
            current_doc_mime_types[file_name] = doc.mimeType
        
        self.logger.info(f"Current document filenames: {current_doc_filenames}")
        
        # Get existing files in vector store using get_workspace_files
        existing_files = {}  # filename -> file_id mapping
        try:
            workspace_files_response = await self.get_workspace_files(workspace_id)
            for file_info in workspace_files_response.files:
                existing_files[file_info.filename] = file_info.file_id
        except Exception as e:
            self.logger.error(f"Failed to get existing files: {str(e)}")
            existing_files = {}
        
        self.logger.info(f"Existing files in vector store: {list(existing_files.keys())}")
        
        # Find files to add and remove
        files_to_add = current_doc_filenames - set(existing_files.keys())
        files_to_remove = set(existing_files.keys()) - current_doc_filenames
        
        self.logger.info(f"Files to add: {files_to_add}")
        self.logger.info(f"Files to remove: {files_to_remove}")
        
        # Remove files that are no longer in the document list
        removed_file_ids = []
        for filename in files_to_remove:
            file_id = existing_files[filename]
            await self.delete_file(workspace_id,file_id)
            self.logger.info(f"Successfully removed file: {filename}")
        for filename in files_to_add:
            mime_type = current_doc_mime_types[filename]
            await self.download_and_insert_file(workspace_id,filename.split(".")[0],request.media_download_url_pattern,CHANNEL_MANAGER_API_KEY,mime_type)
            self.logger.info(f"Successfully inserted file: {filename}")

        self.logger.info(f"File sync completed for workspace {workspace_id}: {len(files_to_add)} files uploaded, {len(files_to_remove)} files removed")
        return SyncFilesResponse(
            vector_store_id=vector_store_id,
            deleted_docs=files_to_remove,
            inserted_docs=files_to_add
        )

    async def get_vector_store_info(self, workspace_id: str) -> VectorStoreInfoResponse:
        """Get vector store information for a workspace."""
        self.logger.info(f"Getting vector store info for workspace: {workspace_id}")
        
        vector_store_id = get_vector_store_id(workspace_id)
        if not vector_store_id:
            self.logger.error(f"No vector store found for workspace: {workspace_id}")
            raise ValueError("No vector store for this workspace")
        
        try:
            vector_store = await self.client.vector_stores.retrieve(vector_store_id)
            self.logger.debug(f"Retrieved vector store: {vector_store.id}")
            
            # Get files from OpenAI directly
            files = []
            async for file in self.client.vector_stores.files.list(vector_store_id=vector_store_id):
                files.append(FileInfo(
                    file_id=file.id,
                    status=file.status,
                    created_at=file.created_at
                ))
            
            self.logger.info(f"Retrieved vector store info with {len(files)} files")
            return VectorStoreInfoResponse(
                vector_store_id=vector_store.id,
                files=files
            )
        except Exception as e:
            self.logger.error(f"Failed to get vector store info for workspace {workspace_id}: {str(e)}")
            raise ValueError("Vector store not found")

    async def get_vector_store_status(self, vector_store_id: str) -> VectorStoreStatusResponse:
        """Get the status of a vector store and all its files."""
        self.logger.info(f"Getting vector store status for: {vector_store_id}")
        
        try:
            # Get vector store info
            vector_store = await self.client.vector_stores.retrieve(vector_store_id)
            self.logger.debug(f"Retrieved vector store info: {vector_store.name}")

            # Get all files in the vector store and their statuses
            file_statuses = []
            status_counts = {
                "in_progress": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0
            }

            async for file in self.client.vector_stores.files.list(vector_store_id=vector_store_id):
                file_status = file.status
                file_statuses.append(FileInfo(
                    file_id=file.id,
                    status=file_status,
                    created_at=file.created_at,
                    bytes=file.usage_bytes
                ))

                # Count statuses
                if file_status in status_counts:
                    status_counts[file_status] += 1

            # Determine overall status
            total_files = len(file_statuses)
            if status_counts["failed"] > 0:
                overall_status = "failed"
            elif status_counts["in_progress"] > 0:
                overall_status = "in_progress"
            elif status_counts["completed"] == total_files and total_files > 0:
                overall_status = "completed"
            elif total_files == 0:
                overall_status = "empty"
            else:
                overall_status = "partial"

            self.logger.info(f"Vector store status: {overall_status}, total files: {total_files}")
            result = VectorStoreStatusResponse(
                vector_store_id=vector_store_id,
                workspace_id=vector_store.name,
                overall_status=overall_status,
                total_files=total_files,
                status_breakdown=StatusBreakdown(**status_counts) if total_files > 0 else None,
                files=file_statuses,
                created_at=vector_store.created_at,
                file_counts=vector_store.file_counts.to_dict()
            )
            return result

        except Exception as e:
            self.logger.error(f"Failed to get vector store status for {vector_store_id}: {str(e)}")
            raise ValueError(f"Vector store not found: {str(e)}")

    async def search_vector_store(self, workspace_id: str, query: str, max_num_results: int = 20) -> dict:
        """Search a vector store for documents matching the query."""
        self.logger.info(f"Starting vector store search: workspace_id={workspace_id}, query='{query}', max_results={max_num_results}")
        
        vector_store_id = get_vector_store_id(workspace_id)
        if not vector_store_id:
            self.logger.error(f"No vector store found for workspace: {workspace_id}")
            raise ValueError("No vector store for this workspace")
        
        try:
            # Create a temporary assistant to use for search
            self.logger.debug(f"Searching vector store: {vector_store_id}")
            documents = await self.client.vector_stores.search(
                vector_store_id=vector_store_id,
                query=query,
                max_num_results=max_num_results
            )
            
            self.logger.info(f"Search completed successfully for workspace: {workspace_id}")
            return documents
            
        except Exception as e:
            self.logger.error(f"Search failed for workspace {workspace_id}: {str(e)}")
            raise ValueError(f"Search failed: {str(e)}")

    async def insert_file(self, workspace_id: str, file_content: bytes, file_name: str) -> FileOperationResponse:
        """Insert a single file into the vector store."""
        self.logger.info(f"Starting file insertion: workspace_id={workspace_id}, file_name={file_name}")
        
        vector_store_id = await self.get_or_create_vector_store_id(workspace_id)
        is_uploaded = False
        try:
            # Upload file to OpenAI
            self.logger.debug(f"Uploading file to OpenAI: {file_name}")
            up = await self.client.files.create(
                file=(file_name, file_content), 
                purpose="assistants"
            )
            
            # Attach file to vector store
            self.logger.debug(f"Attaching file to vector store: {up.id}")
            await self.client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=up.id
            )
            is_uploaded = True
            self.logger.info(f"Successfully inserted file: {file_name} (ID: {up.id})")
            return FileOperationResponse(
                vector_store_id=vector_store_id,
                file_id=up.id,
                file_name=file_name,
                status="uploaded"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to insert file {file_name}: {str(e)}")
            if is_uploaded:
                await self.delete_file(workspace_id, up.id)
    async def download_and_insert_file(self, workspace_id: str, media_id: str, download_url_pattern: str, bearer_token: str, mime_type: str) -> FileOperationResponse:
        """Download a file to temp folder, insert it to OpenAI, then clean up."""
        self.logger.info(f"Starting download and insert: workspace_id={workspace_id}, media_id={media_id}")
        
        file_name = media_id + guess_extension(mime_type.strip())
        temp_file_path = None
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=guess_extension(mime_type.strip())) as temp_file:
                temp_file_path = temp_file.name
                self.logger.debug(f"Created temporary file: {temp_file_path}")
            
            # Download file to temporary location
            self.logger.debug(f"Downloading file to temp location: {temp_file_path}")
            await self.download_file(media_id, download_url_pattern, bearer_token, temp_file_path)
            
            # Read file content
            #TODO: in memory file reading
            async with aiofiles.open(temp_file_path, "rb") as af:
                file_content = await af.read()
            
            # Insert file to OpenAI
            self.logger.debug(f"Inserting file to OpenAI: {file_name}")
            result = await self.insert_file(workspace_id, file_content, file_name)
            
            self.logger.info(f"Successfully downloaded and inserted file: {file_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to download and insert file {media_id}: {str(e)}")
            raise ValueError(f"Failed to download and insert file: {str(e)}")
        
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    self.logger.debug(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary file {temp_file_path}: {str(e)}")

    async def get_vector_store_status_by_workspace(self, workspace_id: str) -> VectorStoreStatusResponse:
        """Get the status of a vector store by workspace ID."""
        self.logger.info(f"Getting vector store status for workspace: {workspace_id}")
        
        vector_store_id = get_vector_store_id(workspace_id)
        if not vector_store_id:
            self.logger.error(f"No vector store found for workspace: {workspace_id}")
            raise ValueError("No vector store for this workspace")
        
        return await self.get_vector_store_status(vector_store_id)

    async def get_workspace_files(self, workspace_id: str) -> WorkspaceFilesResponse:
        """Get all files in a workspace with detailed information."""
        self.logger.info(f"Getting workspace files for: {workspace_id}")
        
        vector_store_id = get_vector_store_id(workspace_id)
        if not vector_store_id:
            self.logger.error(f"No vector store found for workspace: {workspace_id}")
            raise ValueError("No vector store for this workspace")
        
        try:
            files = []
            self.logger.debug(f"Fetching files from vector store: {vector_store_id}")
            async for file in self.client.vector_stores.files.list(vector_store_id=vector_store_id):
                # Get detailed file information
                file_details = await self.client.files.retrieve(file.id)
                files.append(FileInfo(
                    file_id=file.id,
                    filename=file_details.filename,
                    status=file.status,
                    created_at=file.created_at,
                    bytes=file_details.bytes,
                    purpose=file_details.purpose
                ))
            
            self.logger.info(f"Retrieved {len(files)} files for workspace: {workspace_id}")
            return WorkspaceFilesResponse(
                workspace_id=workspace_id,
                vector_store_id=vector_store_id,
                total_files=len(files),
                files=files
            )
        except Exception as e:
            self.logger.error(f"Failed to get workspace files for {workspace_id}: {str(e)}")
            raise ValueError(f"Failed to get workspace files: {str(e)}")

    async def delete_file(self, workspace_id: str, file_id: str) -> FileOperationResponse:
        """Delete a file from the vector store."""
        self.logger.info(f"Starting file deletion: workspace_id={workspace_id}, file_id={file_id}")
        
        vector_store_id = get_vector_store_id(workspace_id)
        if not vector_store_id:
            self.logger.error(f"No vector store found for workspace: {workspace_id}")
            raise ValueError("No vector store for this workspace")
        
        try:
            # Step 1: Remove file from vector store (detaches from vector store)
            self.logger.debug(f"Removing file from vector store: {file_id}")
            await self.client.vector_stores.files.delete(
                vector_store_id=vector_store_id,
                file_id=file_id
            )
            
            # Step 2: Delete the actual file from OpenAI storage (permanent deletion)
            self.logger.debug(f"Deleting file from OpenAI storage: {file_id}")
            await self.client.files.delete(file_id)
            
            self.logger.info(f"Successfully deleted file: {file_id}")
            return FileOperationResponse(
                vector_store_id=vector_store_id,
                file_id=file_id,
                status="deleted"
            )
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_id}: {str(e)}")
            raise ValueError(f"Failed to delete file: {str(e)}")

    async def delete_file_by_name(self, workspace_id: str, file_name: str) -> FileOperationResponse:
        """Delete a file from the vector store by file name."""
        self.logger.info(f"Starting file deletion by name: workspace_id={workspace_id}, file_name={file_name}")
        
        vector_store_id = get_vector_store_id(workspace_id)
        if not vector_store_id:
            self.logger.error(f"No vector store found for workspace: {workspace_id}")
            raise ValueError("No vector store for this workspace")
        
        try:
            # Find the file by name using get_workspace_files
            self.logger.debug(f"Searching for file by name: {file_name}")
            workspace_files_response = await self.get_workspace_files(workspace_id)
            
            file_id = None
            for file_info in workspace_files_response.files:
                if file_info.filename == file_name:
                    file_id = file_info.file_id
                    self.logger.debug(f"Found file {file_name} with ID: {file_id}")
                    break
            
            if not file_id:
                self.logger.error(f"File '{file_name}' not found in vector store")
                raise ValueError(f"File '{file_name}' not found in vector store")
            
            return await self.delete_file(workspace_id, file_id)
        except Exception as e:
            self.logger.error(f"Failed to delete file '{file_name}': {str(e)}")
            raise ValueError(f"Failed to delete file '{file_name}': {str(e)}")


# Create service instance
vector_store_service = VectorStoreService() 