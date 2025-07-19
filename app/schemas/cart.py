from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal 

# Esquema para CartItem
class CartItemCreate(BaseModel):
    menu_item_id: str = Field(..., description="ID del item del menú")
    quantity: int = Field(..., gt=0, le=20, description="Cantidad del item (1-20)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "menu_item_id": "507f1f77bcf86cd799439012",
                "quantity": 2
            }
        }

class CartItemUpdate(BaseModel):
    quantity: int = Field(..., gt=0, le=20, description="Nueva cantidad del item")

    class Config:
        json_schema_extra = {
            "example": {
                "quantity": 3
            }
        }
        
class CartItemResponse(BaseModel):
    id: str = Field(...)
    user_id: str = Field(...)
    menu_item_id: str = Field(...)
    menu_item_name: str = Field(...)
    menu_item_price: Decimal = Field(...)
    quantity: int = Field(...)
    subtotal: Decimal = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439020",
                "user_id": "507f1f77bcf86cd799439011",
                "menu_item_id": "507f1f77bcf86cd799439012",
                "menu_item_name": "Hamburguesa Clásica",
                "menu_item_price": 12.99,
                "quantity": 2,
                "subtotal": 25.98,
                "created_at": "2024-07-18T15:30:00Z",
                "updated_at": "2024-07-18T15:30:00Z"
            }
        }
        
class CartItemWithMenuInfo(CartItemResponse):
    menu_item_description: Optional[str] = Field(None)
    menu_item_image_url: Optional[str] = Field(None)
    menu_item_available: bool = Field(...)
    category_name: Optional[str] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439020",
                "user_id": "507f1f77bcf86cd799439011",
                "menu_item_id": "507f1f77bcf86cd799439012",
                "menu_item_name": "Hamburguesa Clásica",
                "menu_item_description": "Hamburguesa con carne, lechuga y tomate",
                "menu_item_price": 12.99,
                "menu_item_image_url": "https://example.com/burger.jpg",
                "menu_item_available": True,
                "category_name": "Hamburguesas",
                "quantity": 2,
                "subtotal": 25.98,
                "created_at": "2024-07-18T15:30:00Z",
                "updated_at": "2024-07-18T15:30:00Z"
            }
        }
        
class CartSummary(BaseModel):
    items: List[CartItemWithMenuInfo] = Field(...)
    total_items: int = Field(..., description="Cantidad total de items en el carrito")
    total_quantity: int = Field(..., description="Suma de todas las cantidades")
    subtotal: Decimal = Field(..., description="Subtotal de todos los items")
    estimated_tax: Decimal = Field(default=Decimal('0.00'), description="Impuestos estimados")
    estimated_total: Decimal = Field(..., description="Total estimado incluyendo impuestos")
    is_empty: bool = Field(..., description="Si el carrito está vacío")
    last_updated: Optional[datetime] = Field(None, description="Última actualización del carrito")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "507f1f77bcf86cd799439020",
                        "user_id": "507f1f77bcf86cd799439011",
                        "menu_item_id": "507f1f77bcf86cd799439012",
                        "menu_item_name": "Hamburguesa Clásica",
                        "menu_item_description": "Hamburguesa con carne, lechuga y tomate",
                        "menu_item_price": 12.99,
                        "menu_item_image_url": "https://example.com/burger.jpg",
                        "menu_item_available": True,
                        "category_name": "Hamburguesas",
                        "quantity": 2,
                        "subtotal": 25.98,
                        "created_at": "2024-07-18T15:30:00Z",
                        "updated_at": "2024-07-18T15:30:00Z"
                    }
                ],
                "total_items": 1,
                "total_quantity": 2,
                "subtotal": 25.98,
                "estimated_tax": 2.60,
                "estimated_total": 28.58,
                "is_empty": False,
                "last_updated": "2024-07-18T15:30:00Z"
            }
        }

class BulkCartUpdate(BaseModel):
    items: List[CartItemCreate] = Field(..., min_items=1, max_items=50)

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "menu_item_id": "507f1f77bcf86cd799439012",
                        "quantity": 2
                    },
                    {
                        "menu_item_id": "507f1f77bcf86cd799439013",
                        "quantity": 1
                    }
                ]
            }
        }

class CartStats(BaseModel):
    total_users_with_cart: int = Field(..., description="Total de usuarios con items en carrito")
    total_cart_items: int = Field(..., description="Total de items en todos los carritos")
    average_cart_value: Decimal = Field(..., description="Valor promedio de carrito")
    abandoned_carts_24h: int = Field(..., description="Carritos abandonados en 24h")
    most_added_item: Optional[str] = Field(None, description="Item más agregado al carrito")

    class Config:
        json_schema_extra = {
            "example": {
                "total_users_with_cart": 150,
                "total_cart_items": 342,
                "average_cart_value": 23.45,
                "abandoned_carts_24h": 12,
                "most_added_item": "Hamburguesa Clásica"
            }
        }

class CartItemQuickAdd(BaseModel):
    menu_item_id: str = Field(...)
    quantity: int = Field(default=1, gt=0, le=20)

class CartBatchOperation(BaseModel):
    action: str = Field(..., description="Acción a realizar: 'add', 'update', 'remove'")
    items: List[CartItemCreate] = Field(..., min_items=1)

    @validator('action')
    def validate_action(cls, v):
        if v not in ['add', 'update', 'remove']:
            raise ValueError('Action must be: add, update, or remove')
        return v