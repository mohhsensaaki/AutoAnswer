from pymilvus import MilvusClient, DataType
from services.common.log_creator import create_logger
import os
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from services.embedding.openai.embedding_service import create_embeddings
from services.embedding.openai.models import Item
class MilvusServiceBase(ABC):
    """Base service class for handling Milvus operations"""
    
    def __init__(self, uri: str = "http://localhost:19530/", collection_name: str = None, logger=None):
        """Initialize Milvus service with connection"""
        self.client = MilvusClient(uri=uri)
        self.collection_name = collection_name
        self.text_embedding_dimension = int(os.getenv("TEXT_EMBEDDING_DIMENSION", 1536))
        self.media_embedding_dimension = int(os.getenv("MEDIA_EMBEDDING_DIMENSION", 1536))
        self.embedding_service_url = os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8000")
        
        if logger is None:
            is_production = os.getenv("IS_PRODUCTION", "no")
            log_url = os.getenv("LOG_URL", ".")
            self.logger = create_logger(is_production, log_url)
        else:
            self.logger = logger
        
        self._initialize_collection()
    
    @abstractmethod
    def _create_schema(self):
        """Create the schema for the collection - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _get_default_embedding_features(self) -> List[str]:
        """Get default features to embed - must be implemented by subclasses"""
        pass
    
    def _create_indexes(self):
        """Create indexes for the collection to optimize search performance"""
        try:
            # Create index for text_content_embedding vector field
            index_params = MilvusClient.prepare_index_params()
            
            index_params.add_index(
                field_name="text_content_embedding",
                index_type="IVF_FLAT",
                metric_type="COSINE",  # Can be COSINE, L2, or IP
                params={
                    "nlist": 1024  # Number of cluster units
                }
            )
            
            self.client.create_index(
                collection_name=self.collection_name,
                index_params=index_params
            )
            
            self.logger.info(f"Index created for 'text_content_embedding' field in collection '{self.collection_name}'")
            
        except Exception as e:
            self.logger.error(f"Error creating indexes: {str(e)}")
            raise
    
    def _initialize_collection(self):
        """Initialize the collection if it doesn't exist"""
        if os.getenv("IS_PRODUCTION", "no").lower() != "yes":
            # Only drop collection in non-production environments
            if self.client.has_collection(self.collection_name):
                self.client.drop_collection(self.collection_name)
                
        try:
            if not self.client.has_collection(self.collection_name):
                schema = self._create_schema()
                self.client.create_collection(
                    collection_name=self.collection_name,
                    schema=schema
                )
                self.logger.info(f"Collection '{self.collection_name}' created successfully")
                self._create_indexes()
            else:
                self.logger.info(f"Collection '{self.collection_name}' already exists")
            self.client.load_collection(self.collection_name)
        except Exception as e:
            self.logger.error(f"Error initializing collection: {str(e)}")
            raise
    
    async def _get_text_embedding(self, features_to_embed: List[str], **kwargs) -> List[float]:
        """Get text embedding from embedding service for specified features"""
        try:
            # Prepare content by combining specified features
            content_dict = {}
            for feature in features_to_embed:
                if feature in kwargs and kwargs[feature] is not None:
                    # Handle different data types
                    value = kwargs[feature]
                    content_dict[feature] = str(value)
                else:
                    raise Exception(f"No valid content found for embedding, using empty text for feature: {feature}")

            embedding = await create_embeddings(Item(contents=[content_dict], features=list(content_dict.keys())))
            return embedding[0].get("embedding")
        except Exception as e:
            self.logger.error(f"Error getting text embedding: {str(e)}")
            raise Exception(f"Error getting text embedding: {str(e)}")
    
    async def save_record(self, **kwargs) -> Dict[str, Any]:
        """Save record data to Milvus collection - general method for any record type"""
        try:
            # Use default embedding features defined by the class
            features_to_embed = self._get_default_embedding_features()
            
            # Get text embedding from embedding service
            text_embedding = await self._get_text_embedding(features_to_embed=features_to_embed, **kwargs)
            
            # Prepare basic data structure with embedding
            data_to_insert = {}
            
            # Add all provided fields to the data structure
            for key, value in kwargs.items():
                data_to_insert[key] = value
            
            # Always add the embedding field
            data_to_insert["text_content_embedding"] = text_embedding
            
            # Insert data into Milvus
            result = self.client.insert(
                collection_name=self.collection_name,
                data=[data_to_insert]
            )
            
            insert_count = result.get('insert_count', 0)
            self.logger.info(f"Record saved to Milvus successfully. Insert count: {insert_count}")
            
            return {
                "success": True,
                "insert_count": insert_count,
                "message": f"Record saved successfully with {insert_count} records"
            }
            
        except Exception as e:
            error_msg = f"Error saving record to Milvus: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": str(e),
                "message": error_msg
            }
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            if self.client.has_collection(self.collection_name):
                # Get collection statistics
                stats = self.client.get_collection_stats(self.collection_name)
                
                # Get actual schema fields dynamically
                schema = self._create_schema()
                schema_fields = [field.name for field in schema.fields]
                
                return {
                    "collection_name": self.collection_name,
                    "exists": True,
                    "stats": stats,
                    "schema_fields": schema_fields
                }
            else:
                return {
                    "collection_name": self.collection_name,
                    "exists": False,
                    "message": "Collection does not exist"
                }
                
        except Exception as e:
            error_msg = f"Error getting collection info: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": str(e),
                "message": error_msg
            }
    
    async def search_by_vector(self, query_vector: List[float], limit: int = 10, output_fields: List[str] = None) -> Dict[str, Any]:
        """Search for similar records using vector similarity"""
        try:
            if output_fields is None:
                output_fields = ["text_content"]
                
            search_results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                anns_field="text_content_embedding",
                limit=limit,
                output_fields=output_fields
            )
            
            results = []
            for hits in search_results:
                for hit in hits:
                    hit_data = {
                        "distance": hit["distance"], 
                        "entity": hit["entity"]
                    }
                    # Add primary key if available
                    if hasattr(hit, 'id'):
                        hit_data["id"] = hit.id
                    results.append(hit_data)
                    
            return {
                "success": True,
                "results": results,
                "count": len(search_results[0]) if search_results else 0
            }
            
        except Exception as e:
            error_msg = f"Error searching: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": str(e),
                "message": error_msg
            }
    
    async def search_by_text(self, query: str, limit: int = 10, output_fields: List[str] = None) -> Dict[str, Any]:
        """Search for similar records using text query - converts query to vector embedding first"""
        try:
            # Create a temporary dict with the query as text_content for embedding
            query_data = {"text_content": query}
            
            # Get embedding for the query using default features
            default_features = self._get_default_embedding_features()
            query_vector = await self._get_text_embedding(features_to_embed=["text_content"], **query_data)
            
            return await self.search_by_vector(query_vector, limit, output_fields)
            
        except Exception as e:
            error_msg = f"Error searching by text: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": str(e),
                "message": error_msg
            }
    
    def delete_records(self, filter_expression: str) -> Dict[str, Any]:
        """Delete records based on filter expression"""
        try:
            result = self.client.delete(
                collection_name=self.collection_name,
                filter=filter_expression
            )
            
            self.logger.info(f"Records deleted successfully with filter: {filter_expression}")
            
            return {
                "success": True,
                "message": f"Records deleted successfully",
                "filter": filter_expression
            }
            
        except Exception as e:
            error_msg = f"Error deleting records: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": str(e),
                "message": error_msg
            }
    
    def count_records(self, filter_expression: str = None) -> Dict[str, Any]:
        """Count records in the collection"""
        try:
            # Get primary key field name from schema
            schema = self._create_schema()
            primary_field = None
            for field in schema.fields:
                if field.is_primary:
                    primary_field = field.name
                    break
            
            if not primary_field:
                primary_field = "id"  # fallback
            
            search_results = self.client.query(
                collection_name=self.collection_name,
                filter=filter_expression or "",
                output_fields=[primary_field],
            )
            
            count = len(search_results)
            
            return {
                "success": True,
                "count": count,
                "filter": filter_expression
            }
            
        except Exception as e:
            error_msg = f"Error counting records: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": str(e),
                "message": error_msg
            } 