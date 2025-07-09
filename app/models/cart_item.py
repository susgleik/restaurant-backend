from beanie import Document, PydanticObjectId
from pydantic import Field, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal

class CartItem(Document):
    user_id: PydanticObjectId = Field(...)
    menu_item_id: PydanticObjectId = Field(...)
    menu_item_name: str = Field(..., min_length=1, max_length=100)
    menu_item_price: Decimal = Field(..., gt=0, decimal_places=2)
    quantity: int = Field(..., gt=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('menu_item_price', pre=True)
    def validate_price(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
    @property
    def subtotal(self) -> Decimal:
        """Calcula el subtotal del item del carrito"""
        return self.menu_item_price * self.quantity
    
    class Settings:
        name = "cart_items"
        indexes = [
            "user_id",
            "menu_item_id",
            ("user_id", "menu_item_id"),  # Índice compuesto
            "created_at",
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "menu_item_id": "507f1f77bcf86cd799439012",
                "menu_item_name": "Hamburguesa Clásica",
                "menu_item_price": 12.99,
                "quantity": 2
            }
        }