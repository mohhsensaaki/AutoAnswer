import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from services.common.milvus_service_base import MilvusServiceBase
from pymilvus import FieldSchema, CollectionSchema, DataType
from typing import List, Dict, Any


class DocumentMilvusService(MilvusServiceBase):
    """Milvus service for handling document operations with document_id, and text_content"""
    
    def __init__(self, uri: str = "http://localhost:19530/", collection_name: str = "documents", logger=None):
        """Initialize Document Milvus service"""
        super().__init__(uri=uri, collection_name=collection_name, logger=logger)
    
    def _create_schema(self):
        """Create the schema for the document collection"""
        # Define fields for the schema
        fields = [
            FieldSchema(
                name="id", 
                dtype=DataType.INT64, 
                is_primary=True, 
                auto_id=True,
                description="Primary key ID (auto-generated)"
            ),
            FieldSchema(
                name="document_id", 
                dtype=DataType.VARCHAR, 
                max_length=512,
                description="Unique document identifier"
            ),
            FieldSchema(
                name="text_content", 
                dtype=DataType.VARCHAR, 
                max_length=65535,  # 64KB max for text content
                description="The text content of the document"
            ),
            FieldSchema(
                name="text_content_embedding", 
                dtype=DataType.FLOAT_VECTOR, 
                dim=self.text_embedding_dimension,
                description="Vector embedding of the text content"
            ),
        ]
        
        # Create and return schema
        schema = CollectionSchema(
            fields=fields,
            description="Document collection for storing documents with embeddings",
            enable_dynamic_field=True  # Allow additional fields to be added dynamically
        )
        
        return schema
    
    def _get_default_embedding_features(self) -> List[str]:
        """Get default features to embed - returns text_content as the main embedding feature"""
        return ["text_content"]
    
    async def save_document(self, document_id: str,  text_content: str) -> Dict[str, Any]:
        """Save a document to the Milvus collection"""
        return await self.save_record(
            document_id=document_id,
            text_content=text_content
        )
    
    async def search_documents_by_text(self, query: str, limit: int = 10, output_fields: List[str] = None) -> Dict[str, Any]:
        """Search documents by text content"""
        if output_fields is None:
            output_fields = ["document_id", "text_content"]
        
        return await self.search_by_text(query=query, limit=limit, output_fields=output_fields)
    
    async def search_documents_by_vector(self, query_vector: List[float], limit: int = 10, output_fields: List[str] = None) -> Dict[str, Any]:
        """Search documents by vector similarity"""
        if output_fields is None:
            output_fields = ["document_id", "text_content"]
        
        return await self.search_by_vector(query_vector=query_vector, limit=limit, output_fields=output_fields)
    
    def delete_documents(self, filter_expression: str) -> Dict[str, Any]:
        """Delete documents based on filter expression"""
        return self.delete_records(filter_expression=filter_expression)
    
    def count_documents(self, filter_expression: str = None) -> Dict[str, Any]:
        """Count documents in the collection"""
        return self.count_records(filter_expression=filter_expression)
    
    def get_documents_info(self) -> Dict[str, Any]:
        """Get information about the documents collection"""
        return self.get_collection_info() 