import os
from pathlib import Path
from dotenv import load_dotenv
from services.common.log_creator import create_logger
from services.embedding.openai.models import Item
import litellm
import asyncio

# Load environment variables from .env file in the same directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Get all environment variables
EMBEDDING_MODEL = os.getenv("LITELLM_MODEL_NAME", 'text-embedding-3-small')
IS_PRODUCTION = os.getenv("IS_PRODUCTION", 'no')
LOG_URL = os.getenv('LOG_URL', './logs')

# Initialize logger
logger = create_logger(IS_PRODUCTION, LOG_URL)


async def health_check():
    return {"status": "ok"}


async def create_embeddings(item: Item):
    """
    This endpoint is used to create embeddings for the given input data.
    This endpoint send request to litellm to create embeddings.
    """
    logger.info('Embedding service => create_embeddings endpoint is started.')
    # Process each item in the input JSON
    content_to_embed_items = list()

    for content in item.contents:
        content_to_embed = " | ".join([f"{feature}: + {content.get(feature)}" for feature in item.features])
        content_to_embed_items.append(content_to_embed)

    if not content_to_embed_items:
        raise ValueError(f"No content provided to embed for ids: {item.id}")
    logger.info('Embedding service => content to embed: '+ str(content_to_embed_items)[:10])
    response = litellm.embedding(model=EMBEDDING_MODEL, input=content_to_embed_items)

    logger.info("Embedding service => create_embeddings endpoint is completed.")

    return response.data


async def main():
    """
    Main function to test the embedding service functionality.
    """
    print("Testing Embedding Service...")
    
    # Create sample test data
    sample_item = Item(
        contents=[
            {
                "id": "test_001",
                "title": "Introduction to Machine Learning",
                "description": "A comprehensive guide to understanding machine learning concepts and applications.",
                "category": "education"
            },
            {
                "id": "test_002", 
                "title": "Python Programming Basics",
                "description": "Learn the fundamentals of Python programming language.",
                "category": "programming"
            }
        ],
        features=["title", "description", "category"]
    )
    
    try:
        # Test health check
        health_status = await health_check()
        print(f"Health Check: {health_status}")
        
        # Test embedding creation
        print("Creating embeddings for sample data...")
        embeddings = await create_embeddings(sample_item)
        
        print(f"Successfully created {len(embeddings)} embeddings")
        for i, embedding in enumerate(embeddings):
            print(f"Embedding {i+1}: dimension = {len(embedding.get('embedding'))}")
            print(f"Model used: {embedding.get('model')}")
            print(f"Usage: {embedding.get('usage')}")
            print("---")
            
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        logger.error(f"Error in main function: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())

