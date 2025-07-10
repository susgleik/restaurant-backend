from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Nombre de la categoría")
    description: Optional[str] = Field(None, max_length=500, description="Descripción de la categoría")
    active: bool = Field(default=True, description="Indica si la categoría está activa")
    
class CategoryCreate(CategoryBase):
    """Schema para crear una nueva categoría"""
    pass

class CategoryUpdate(BaseModel):
    """Schema para actualizar una categoría existente"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Nuevo nombre de la categoría")
    description: Optional[str] = Field(None, max_length=500, description="Nueva descripción de la categoría")
    active: Optional[bool] = Field(None, description="Nuevo estado de actividad de la categoría")
    
class CategoryResponse(CategoryBase):
    """Schema para la respuesta de una categoría"""
    id: str = Field(..., description="ID único de la categoría")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "Bebidas",
                "description": "Bebidas frías y calientes",
                "active": True,
                "created_at": "2023-10-01T12:00:00Z"
            }
        }
        
class CategoryList(BaseModel):
    """Schema para listar categorías"""
    categories: list[CategoryResponse] = Field(..., description="Lista de categorías")
    total: int = Field(..., description="Total de categorías disponibles")
    
    class Config:
        json_schema_extra = {
            "example": {
                "categories": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "name": "Bebidas",
                        "description": "Bebidas frías y calientes",
                        "active": True,
                        "created_at": "2023-10-01T12:00:00Z"
                    }
                ],
                "total": 1
            }
        }

    