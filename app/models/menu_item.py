from beanie import Document, PydanticObjectId
from pydantic import Field, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal

class MenuItem(Document):
    category_id: PydanticObjectId = Field(...)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Decimal = Field(..., gt=0, decimal_places=2)
    image_url: Optional[str] = Field(None, max_length=500)
    available: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('price', pre=True)
    def validate_price(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
    class Settings:
        name = "menu_items"
        indexes = [
            "category_id",
            "name",
            "available",
            "price",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "category_id": "507f1f77bcf86cd799439011",
                "name": "Hamburguesa Clásica",
                "description": "Hamburguesa con carne, lechuga, tomate y queso",
                "price": 12.99,
                "image_url": "https://example.com/burger.jpg",
                "available": True
            }
        }