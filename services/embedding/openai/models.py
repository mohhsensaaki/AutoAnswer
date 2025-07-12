from pydantic import BaseModel, Field
from typing import List, Dict


class Item(BaseModel):
    """
    Model for embedding request data.
    
    Attributes:
        contents: List of dictionaries containing the content to be embedded
        features: List of feature names to be used for embedding
    """
    contents: List[Dict] = Field(
        example=[
            {
                "id": "123",
                "title": "Sample Title",
                "description": "This is a sample description",
                "category": "sample_category"
            },
            {
                "id": "456",
                "title": "Another Title",
                "description": "Another sample description",
                "category": "another_category"
            }
        ],
        description="List of content items to be embedded. Each item should be a dictionary with the specified features."
    )
    features: List[str] = Field(
        example=["title", "description", "category"],
        description="List of feature names to be used for creating the embedding. These should match the keys in the content dictionaries."
    )
