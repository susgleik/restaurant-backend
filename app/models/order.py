from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
from bson import Decimal128

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
    @classmethod
    def validate_decimals(cls, v):
        """Convertir Decimal128 de MongoDB a Decimal de Python"""
        if isinstance(v, Decimal128):
            return Decimal(str(v.to_decimal()))
        elif isinstance(v, (int, float)):
            return Decimal(str(v))
        elif isinstance(v, str):
            return Decimal(v)
        elif isinstance(v, Decimal):
            return v
        else:
            raise ValueError(f"Tipo de precio no soportado: {type(v)}")
    
    @validator('subtotal')
    @classmethod
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
    @classmethod
    def validate_total(cls, v):
        """Convertir Decimal128 de MongoDB a Decimal de Python"""
        if isinstance(v, Decimal128):
            return Decimal(str(v.to_decimal()))
        elif isinstance(v, (int, float)):
            return Decimal(str(v))
        elif isinstance(v, str):
            return Decimal(v)
        elif isinstance(v, Decimal):
            return v
        else:
            raise ValueError(f"Tipo de total no soportado: {type(v)}")
    
    @validator('total')
    @classmethod
    def validate_total_amount(cls, v, values):
        if 'items' in values and values['items']:
            calculated_total = sum(item.subtotal for item in values['items'])
            if abs(v - calculated_total) > Decimal('0.01'):
                raise ValueError('Total does not match sum of item subtotals')
        return v
    
    def dict(self, **kwargs):
        """Override dict method para asegurar conversión correcta"""
        data = super().dict(**kwargs)
        # Asegurar que total sea Decimal
        if 'total' in data and isinstance(data['total'], Decimal128):
            data['total'] = Decimal(str(data['total'].to_decimal()))
        
        # Asegurar que items tengan precios como Decimal
        if 'items' in data:
            for item in data['items']:
                if 'unit_price' in item and isinstance(item['unit_price'], Decimal128):
                    item['unit_price'] = Decimal(str(item['unit_price'].to_decimal()))
                if 'subtotal' in item and isinstance(item['subtotal'], Decimal128):
                    item['subtotal'] = Decimal(str(item['subtotal'].to_decimal()))
        
        return data
    
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