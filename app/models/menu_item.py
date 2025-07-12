from beanie import Document, PydanticObjectId
from pydantic import Field, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from bson import Decimal128

class MenuItem(Document):
    category_id: PydanticObjectId = Field(...)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Decimal = Field(..., gt=0)
    image_url: Optional[str] = Field(None, max_length=500)
    available: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('price', pre=True)
    @classmethod
    def validate_price(cls, v):
        """Convertir Decimal128 de MongoDB a Decimal de Python"""
        if isinstance(v, Decimal128):
            # Convertir Decimal128 a Decimal
            return Decimal(str(v.to_decimal()))
        elif isinstance(v, (int, float)):
            return Decimal(str(v))
        elif isinstance(v, str):
            return Decimal(v)
        elif isinstance(v, Decimal):
            return v
        else:
            raise ValueError(f"Tipo de precio no soportado: {type(v)}")
    
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
    
    def dict(self, **kwargs):
        """Override dict method para asegurar conversión correcta"""
        data = super().dict(**kwargs)
        # Asegurar que price sea Decimal
        if 'price' in data and isinstance(data['price'], Decimal128):
            data['price'] = Decimal(str(data['price'].to_decimal()))
        return data