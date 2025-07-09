from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    IN_PREPARATION = "IN_PREPARATION"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class OrderItem(BaseModel):
    menu_item_id: PydanticObjectId = Field(...)
    menu_item_name: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., gt=0, decimal_places=2)
    subtotal: Decimal = Field(..., gt=0, decimal_places=2)
    special_instructions: Optional[str] = Field(None, max_length=200)
    
    @validator('unit_price', 'subtotal', pre=True)
    def validate_decimals(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
    @validator('subtotal')
    def validate_subtotal(cls, v, values):
        if 'quantity' in values and 'unit_price' in values:
            expected_subtotal = values['quantity'] * values['unit_price']
            if abs(v - expected_subtotal) > Decimal('0.01'):
                raise ValueError('Subtotal does not match quantity * unit_price')
        return v

class Order(Document):
    user_id: PydanticObjectId = Field(...)
    items: List[OrderItem] = Field(..., min_items=1)
    total: Decimal = Field(..., gt=0, decimal_places=2)
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    notes: Optional[str] = Field(None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('total', pre=True)
    def validate_total(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
    @validator('total')
    def validate_total_amount(cls, v, values):
        if 'items' in values:
            calculated_total = sum(item.subtotal for item in values['items'])
            if abs(v - calculated_total) > Decimal('0.01'):
                raise ValueError('Total does not match sum of item subtotals')
        return v
    
    class Settings:
        name = "orders"
        indexes = [
            "user_id",
            "status",
            "created_at",
            ("user_id", "status"),
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "items": [
                    {
                        "menu_item_id": "507f1f77bcf86cd799439012",
                        "menu_item_name": "Hamburguesa Clásica",
                        "quantity": 2,
                        "unit_price": 12.99,
                        "subtotal": 25.98,
                        "special_instructions": "Sin cebolla"
                    }
                ],
                "total": 25.98,
                "status": "PENDING",
                "notes": "Entrega rápida por favor"
            }
        }