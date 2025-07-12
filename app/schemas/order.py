from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from app.models.order import OrderStatus

class OrderItemCreate(BaseModel):
    menu_item_id: str = Field(..., description="ID del artículo del menú")
    quantity: int = Field(..., gt=0, description="Cantidad del item")
    special_instructions: Optional[str] = Field(None, max_length=200, description="Instrucciones especiales")

class OrderItemResponse(BaseModel):
    menu_item_id: str = Field(...)
    menu_item_name: str = Field(...)
    quantity: int = Field(...)
    unit_price: Decimal = Field(...)
    subtotal: Decimal = Field(...)
    special_instructions: Optional[str] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "menu_item_id": "507f1f77bcf86cd799439012",
                "menu_item_name": "Hamburguesa Clásica",
                "quantity": 2,
                "unit_price": 12.99,
                "subtotal": 25.98,
                "special_instructions": "Sin cebolla"
            }
        }

# Esquemas para Order
class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_items=1, description="Lista de items del pedido")
    notes: Optional[str] = Field(None, max_length=500, description="Notas adicionales del pedido")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "menu_item_id": "507f1f77bcf86cd799439012",
                        "quantity": 2,
                        "special_instructions": "Sin cebolla"
                    },
                    {
                        "menu_item_id": "507f1f77bcf86cd799439013",
                        "quantity": 1,
                        "special_instructions": "Extra queso"
                    }
                ],
                "notes": "Entrega rápida por favor"
            }
        }

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = Field(None, description="Nuevo estado del pedido")
    notes: Optional[str] = Field(None, max_length=500, description="Nuevas notas del pedido")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "IN_PREPARATION",
                "notes": "Preparando con ingredientes frescos"
            }
        }

class OrderResponse(BaseModel):
    id: str = Field(...)
    user_id: str = Field(...)
    items: List[OrderItemResponse] = Field(...)
    total: Decimal = Field(...)
    status: OrderStatus = Field(...)
    notes: Optional[str] = Field(None)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439015",
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
                "notes": "Entrega rápida por favor",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }

class OrderList(BaseModel):
    orders: List[OrderResponse] = Field(...)
    total: int = Field(..., description="Total de pedidos encontrados")

    class Config:
        json_schema_extra = {
            "example": {
                "orders": [
                    {
                        "id": "507f1f77bcf86cd799439015",
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
                        "notes": "Entrega rápida por favor",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }

class OrderWithUserInfo(OrderResponse):
    username: Optional[str] = Field(None, description="Nombre del usuario")
    user_email: Optional[str] = Field(None, description="Email del usuario")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439015",
                "user_id": "507f1f77bcf86cd799439011",
                "username": "john_doe",
                "user_email": "john@example.com",
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
                "notes": "Entrega rápida por favor",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }

class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(..., description="Nuevo estado del pedido")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "IN_PREPARATION"
            }
        }

class OrderFilters(BaseModel):
    status: Optional[OrderStatus] = Field(None, description="Filtrar por estado")
    user_id: Optional[str] = Field(None, description="Filtrar por usuario")
    date_from: Optional[datetime] = Field(None, description="Fecha desde")
    date_to: Optional[datetime] = Field(None, description="Fecha hasta")
    min_total: Optional[Decimal] = Field(None, ge=0, description="Total mínimo")
    max_total: Optional[Decimal] = Field(None, ge=0, description="Total máximo")

class OrderStats(BaseModel):
    total_orders: int = Field(..., description="Total de pedidos")
    pending_orders: int = Field(..., description="Pedidos pendientes")
    in_preparation_orders: int = Field(..., description="Pedidos en preparación")
    ready_orders: int = Field(..., description="Pedidos listos")
    delivered_orders: int = Field(..., description="Pedidos entregados")
    cancelled_orders: int = Field(..., description="Pedidos cancelados")
    total_revenue: Decimal = Field(..., description="Ingresos totales")
    average_order_value: Decimal = Field(..., description="Valor promedio del pedido")

    class Config:
        json_schema_extra = {
            "example": {
                "total_orders": 150,
                "pending_orders": 5,
                "in_preparation_orders": 3,
                "ready_orders": 2,
                "delivered_orders": 135,
                "cancelled_orders": 5,
                "total_revenue": 2450.75,
                "average_order_value": 16.34
            }
        }