# OpenAI Vector Store Service

This service manages OpenAI vector stores with PostgreSQL as the backend database.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Database Setup
- Install and start PostgreSQL
- Create a database (default name: `vector_store_db`)

### 3. Environment Configuration
1. Copy the environment template:
```bash
cp env_config.template .env
```

2. Edit `.env` file with your actual configuration:
```env
# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vector_store_db
DB_USER=postgres
DB_PASSWORD=your_actual_password

# OpenAI Configuration
OPENAI_API_KEY=your_actual_openai_api_key

# Channel Manager Configuration
CHANNEL_MANAGER_API_KEY=your_actual_channel_manager_api_key
```

### 4. Run the Service
```bash
uvicorn openai_vector_store_service:app --reload --port 8000
```

## Database Schema

The service automatically creates the following table if it doesn't exist:

```sql
CREATE TABLE IF NOT EXISTS vector_store_map (
    workspace_id TEXT PRIMARY KEY,
    vector_store_id TEXT NOT NULL
);
```

## Architecture

The service is now split into:
- `openai_vector_store_service.py` - Main FastAPI app
- `vector_store_service.py` - Business logic for OpenAI operations
- `vector_store_router.py` - API endpoints/routes
- `db.py` - PostgreSQL database operations

## API Endpoints

All endpoints are prefixed with `/api/v1`:

- `POST /api/v1/sync-files` - Sync files to OpenAI vector store
- `GET /api/v1/vector-store/{workspace_id}` - Get vector store info
- `GET /api/v1/vector-store-status/{vector_store_id}` - Get vector store status by vector store ID
- `GET /api/v1/vector-store-status-by-workspace/{workspace_id}` - Get vector store status by workspace ID
- `GET /api/v1/workspace-files/{workspace_id}` - Get all files in a workspace with detailed info
- `POST /api/v1/vector-store-search` - Search in vector store
- `POST /api/v1/insert-file` - Insert a single file into vector store
- `DELETE /api/v1/delete-file` - Delete a file from vector store by file ID (also deletes from OpenAI storage)
- `DELETE /api/v1/delete-file-by-name` - Delete a file from vector store by file name (also deletes from OpenAI storage)

## File Deletion Behavior

When deleting files, the service performs a **complete deletion**:
1. **Detaches** the file from the vector store
2. **Permanently deletes** the file from OpenAI storage

This ensures no orphaned files remain in your OpenAI account and prevents unexpected storage costs. 