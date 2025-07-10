from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from decimal import Decimal

class MenuItemBase(BaseModel):
    category_id: str = Field(..., description="ID de la categoría")
    name: str = Field(..., min_length=2, max_length=100, description="Nombre del item")
    description: Optional[str] = Field(None, max_length=500, description="Descripción del item")
    price: Decimal = Field(..., gt=0, decimal_places=2, description="Precio del item")
    image_url: Optional[str] = Field(None, max_length=500, description="URL de la imagen")
    available: bool = Field(default=True, description="Si el item está disponible")
    
    @validator('price', pre=True)
    def validate_price(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
class MenuItemCreate(MenuItemBase):
    """Schema para crear un nuevo item del menú"""
    pass
    
class MenuItemUpdate(BaseModel):
    """Schema para actualizar un item del menú existente"""
    category_id: Optional[str] = Field(None, description="ID de la categoría")
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Nombre del item")
    description: Optional[str] = Field(None, max_length=500, description="Descripción del item")
    price: Decimal = Field(..., gt=0, description="Precio del item")
    image_url: Optional[str] = Field(None, max_length=500, description="URL de la imagen")
    available: Optional[bool] = Field(None, description="Si el item está disponible")
    
    @validator('price', pre=True)
    def validate_price(cls, v):
        if v is not None and isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

class MenuItemResponse(MenuItemBase):
    """Schema para respuesta de item del menú"""
    id: str = Field(..., description="ID único del item")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "category_id": "507f1f77bcf86cd799439012",
                "name": "Hamburguesa Clásica",
                "description": "Hamburguesa con carne, lechuga, tomate y queso",
                "price": 12.99,
                "image_url": "https://example.com/burger.jpg",
                "available": True,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z"
            }
        }
        
class MenuItemWithCategory(MenuItemResponse):
    """Schema para item del menú con información de categoría"""
    category_name: Optional[str] = Field(None, description="Nombre de la categoría")
    category_active: Optional[bool] = Field(None, description="Si la categoría está activa")

class MenuItemList(BaseModel):
    """Schema para lista de items del menú"""
    items: list[MenuItemResponse] = Field(..., description="Lista de items del menú")
    total: int = Field(..., description="Total de items")
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "category_id": "507f1f77bcf86cd799439012",
                        "name": "Hamburguesa Clásica",
                        "description": "Hamburguesa con carne, lechuga, tomate y queso",
                        "price": 12.99,
                        "image_url": "https://example.com/burger.jpg",
                        "available": True,
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:00:00Z"
                    }
                ],
                "total": 1
            }
        }
        
class MenuItemFilters(BaseModel):
    """Schema para filtros de búsqueda de items del menú"""
    category_id: Optional[str] = Field(None, description="Filtrar por categoría")
    available: Optional[bool] = Field(None, description="Filtrar por disponibilidad")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Precio mínimo")
    max_price: Optional[Decimal] = Field(None, ge=0, description="Precio máximo")
    search: Optional[str] = Field(None, min_length=1, max_length=100, description="Buscar en nombre o descripción")
    
    @validator('min_price', 'max_price', pre=True)
    def validate_prices(cls, v):
        if v is not None and isinstance(v, (int, float)):
            return Decimal(str(v))
        return v