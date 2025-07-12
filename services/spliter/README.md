# Content Splitter Service

A LangChain-powered service for downloading content from URLs and splitting it into semantic chunks for vector storage. Supports PDF, DOCX, and JSON files with intelligent splitting methods.

## Features

- **Advanced Text Splitting**: 9 LangChain-powered splitting methods including semantic chunking
- **Multi-Document Processing**: Batch processing of multiple documents in a single request
- **File Format Support**: PDF, DOCX, and JSON documents
- **Bearer Token Authentication**: Support for protected content endpoints
- **Semantic Chunking**: AI-powered semantic splitting using LangChain's SemanticChunker
- **Preview Mode**: Test splitting without saving to database
- **Milvus Integration**: Automatic vector storage with existing Milvus document service

## API Endpoints

### Split Documents
**POST** `/split-url`

Split documents and save chunks to Milvus vector database.

**Request:**
```json
{
  "documents": [
    {
      "id": "doc_123",
      "createdAt": "2024-01-15T10:30:00Z",
      "lastModifiedAt": "2024-01-15T10:30:00Z",
      "mimeType": "application/pdf"
    }
  ],
  "media_download_url_pattern": "https://api.example.com/file/{media_id}",
  "split_method": "recursive_character",
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "bearer_token": "your_bearer_token"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Documents processed successfully",
  "data": {
    "total_documents": 1,
    "processed_documents": 1,
    "failed_documents": 0,
    "total_chunks": 15,
    "processing_results": [...]
  }
}
```

### Preview Split
**POST** `/split-url-preview`

Preview how documents would be split without saving to database.

Same request format as `/split-url`, but chunks are not saved to Milvus.

### Health Check
**GET** `/health`

Check service health and Milvus connection status.

### Service Info
**GET** `/info`

Get detailed information about supported features and splitting methods.

## Split Methods

| Method | Description | Best For |
|--------|-------------|----------|
| `recursive_character` | Hierarchical splitting by multiple separators | General text content (default) |
| `character` | Simple splitting by single separator | Uniform text structure |
| `token` | Token-based splitting using GPT-4 encoding | LLM processing |
| `markdown` | Markdown-aware structure preservation | Documentation |
| `html` | HTML-aware splitting by headers | Web content |
| `code_python` | Python code structure awareness | Python source code |
| `code_javascript` | JavaScript code structure awareness | JS source code |
| `sentence` | Sentence boundary preservation | Natural language |
| `semantic` | AI-powered semantic grouping | Content requiring semantic coherence |

## Document Processing

### Supported Formats
- **PDF**: Text extraction using PyPDFLoader and PDFPlumberLoader
- **DOCX**: Text extraction using Docx2txtLoader and UnstructuredWordDocumentLoader  
- **JSON**: Structured data processing using JSONLoader

### URL Pattern System
Documents are downloaded using a URL pattern where `{media_id}` is replaced with the document ID:
```
https://api2.didbi.com/gw/v1/ai/file/{media_id}
```

### Processing Flow
1. **Document Download**: Fetch content using constructed URLs with optional bearer token
2. **Content Extraction**: Extract text using appropriate LangChain document loaders
3. **Intelligent Splitting**: Apply selected LangChain text splitter
4. **Chunk Generation**: Create chunks with metadata and unique IDs
5. **Vector Storage**: Save to Milvus with embeddings (when not in preview mode)

## Configuration

### Environment Variables
```bash
# Milvus Configuration
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_DB_NAME=default
MILVUS_COLLECTION_NAME=document_vectors

# OpenAI Configuration (for semantic splitting)
OPENAI_API_KEY=your_openai_api_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `documents` | Array | Required | List of documents to process |
| `media_download_url_pattern` | String | Required | URL pattern with {media_id} placeholder |
| `split_method` | Enum | `recursive_character` | LangChain splitting method |
| `chunk_size` | Integer | 1000 | Target chunk size (characters/tokens) |
| `chunk_overlap` | Integer | 200 | Overlap between consecutive chunks |
| `document_id_prefix` | String | null | Prefix for generated document IDs |
| `separators` | Array | null | Custom separators for splitting |
| `keep_separator` | Boolean | true | Whether to preserve separators in chunks |
| `bearer_token` | String | null | Authentication token for downloads |
| `semantic_similarity_threshold` | Float | 0.75 | Threshold for semantic chunking (0.0-1.0) |

## Usage Examples

### Single Document Processing
```json
{
  "documents": [
    {
      "id": "report_2024",
      "createdAt": "2024-01-15T10:30:00Z",
      "lastModifiedAt": "2024-01-15T10:30:00Z", 
      "mimeType": "application/pdf"
    }
  ],
  "media_download_url_pattern": "https://api2.didbi.com/gw/v1/ai/file/{media_id}",
  "split_method": "recursive_character",
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

### Multiple Document Processing
```json
{
  "documents": [
    {
      "id": "doc1",
      "createdAt": "2024-01-15T10:30:00Z",
      "lastModifiedAt": "2024-01-15T10:30:00Z",
      "mimeType": "application/pdf"
    },
    {
      "id": "doc2", 
      "createdAt": "2024-01-15T11:00:00Z",
      "lastModifiedAt": "2024-01-15T11:00:00Z",
      "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
  ],
  "media_download_url_pattern": "https://api2.didbi.com/gw/v1/ai/file/{media_id}",
  "split_method": "semantic",
  "semantic_similarity_threshold": 0.8
}
```

### Semantic Splitting
```json
{
  "documents": [...],
  "media_download_url_pattern": "https://api2.didbi.com/gw/v1/ai/file/{media_id}",
  "split_method": "semantic",
  "semantic_similarity_threshold": 0.75,
  "bearer_token": "Bearer your_token_here"
}
```

## Error Handling

The service provides comprehensive error handling with detailed messages:

- **Invalid file types**: Only PDF, DOCX, and JSON are supported
- **Download failures**: Network errors, authentication issues
- **Processing errors**: Content extraction or splitting failures  
- **Milvus errors**: Database connection or storage issues

## Integration

### With Existing Services
- **Milvus Document Service**: Automatic chunk storage and retrieval
- **OpenAI Embedding Service**: Vector generation for semantic search
- **FastAPI Router**: RESTful API endpoints with response formatting

### Response Format
All responses follow the standardized format:
```json
{
  "success": boolean,
  "message": "Description of operation result",
  "data": {}, // Operation-specific data
  "error": "Error description if applicable"
}
```

## Development

### Dependencies
- LangChain (text splitting and document loading)
- FastAPI (web framework)
- Pydantic (data validation)
- PyMuPDF/PDFPlumber (PDF processing)
- python-docx (DOCX processing)
- OpenAI (embeddings for semantic splitting)

### Testing
Use the preview endpoints to test splitting without database modifications:
```bash
curl -X POST "http://localhost:8000/split-url-preview" \
  -H "Content-Type: application/json" \
  -d '{...request_payload...}'
``` 