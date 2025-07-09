from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime

class Category(Document):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "categories"
        indexes = [
            "name",
            "active",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Bebidas",
                "description": "Bebidas frías y calientes",
                "active": True
            }
        }