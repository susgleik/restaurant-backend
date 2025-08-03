from fastapi import APIRouter, HTTPException, Depends, status, Query, File, UploadFile
from typing import Optional
from beanie import PydanticObjectId
from datetime import datetime
from decimal import Decimal

from app.schemas.menu_item import (
     MenuItemCreate, 
    MenuItemUpdate, 
    MenuItemResponse, 
    MenuItemList,
    MenuItemFilters,
    MenuItemWithCategory
)

from app.models.menu_item import MenuItem
from app.models.category import Category
from app.models.user import User
from app.core.deps import get_current_admin_user
from app.core.security import get_current_active_user
from app.config import settings

# import azure dependencies if using Azure
if settings.use_azure_storage:
    from app.utils.azure_image_utils import AzureImageProcessor
    
router = APIRouter()
        
#get menu items 
@router.get(
    "/",
    response_model=MenuItemList,
    summary="Obtener todos los items del menú",
    description="Obtener lista de todos los items del menú con filtros opcionales",
)
async def get_menu_items(
    
    category_id: Optional[str] = Query(None, description="Filtrar por categoría"),
    available: Optional[bool] = Query(None, description="Filtrar por disponibilidad"),
    min_price: Optional[Decimal] = Query(None, ge=0, description="Precio mínimo"),
    max_price: Optional[Decimal] = Query(None, ge=0, description="Precio máximo"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Buscar en nombre o descripción"),
    skip: int = Query(0, ge=0, description="Número de items a saltar"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de items a retornar")
):
    """
    Obtener lista de items del menú:
    
    - **category_id**: Filtrar por categoría específica
    - **available**: Filtrar solo items disponibles
    - **min_price**: Precio mínimo
    - **max_price**: Precio máximo
    - **search**: Buscar en nombre o descripción
    - **skip**: Número de items a saltar (paginación)
    - **limit**: Número máximo de items a retornar
    
    No requiere autenticación.
    """
    try:
        # Construir filtros
        filters = {}
        
        if category_id:
            if not PydanticObjectId.is_valid(category_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID de categoría inválido"
                )
            filters["category_id"] = PydanticObjectId(category_id)
        
        if available is not None:
            filters["available"] = available
        
        if min_price is not None or max_price is not None:
            price_filter = {}
            if min_price is not None:
                price_filter["$gte"] = min_price
            if max_price is not None:
                price_filter["$lte"] = max_price
            filters["price"] = price_filter
        
        if search:
            # Búsqueda de texto en nombre y descripción
            filters["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]
        
        # Obtener items con paginación
        items = await MenuItem.find(filters).skip(skip).limit(limit).to_list()
        
        # Contar total
        total = await MenuItem.find(filters).count()
        
        # Convertir a respuesta
        item_responses = [
            MenuItemResponse(
                id=str(item.id),
                category_id=str(item.category_id),
                name=item.name,
                description=item.description,
                price=item.price,
                image_url=item.image_url,
                available=item.available,
                created_at=item.created_at,
                updated_at=item.updated_at
            ) for item in items
        ]
        
        return MenuItemList(
            items=item_responses,
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener items del menú: {str(e)}"
        )

@router.get(
    "/{item_id}",
    response_model=MenuItemWithCategory,
    summary="Obtener item del menú por ID",
    description="Obtener información de un item específico con datos de la categoría"
)
async def get_menu_item(item_id: str):
    """
    Obtener item del menú por ID:
    
    - **item_id**: ID único del item
    
    No requiere autenticación.
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de item inválido"
            )
        
        # Buscar item
        item = await MenuItem.get(PydanticObjectId(item_id))
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item del menú no encontrado"
            )
        
        # Obtener información de la categoría
        category = await Category.get(item.category_id)
        
        return MenuItemWithCategory(
            id=str(item.id),
            category_id=str(item.category_id),
            name=item.name,
            description=item.description,
            price=item.price,
            image_url=item.image_url,
            available=item.available,
            created_at=item.created_at,
            updated_at=item.updated_at,
            category_name=category.name if category else None,
            category_active=category.active if category else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener item del menú: {str(e)}"
        )
    
@router.get(
    "/category/{category_id}",
    response_model=MenuItemList,
    summary="Obtener items por categoría",
    description="Obtener todos los items de una categoría específica"
)
async def get_menu_items_by_category(
    category_id: str,
    available_only: bool = Query(True, description="Solo items disponibles"),
    skip: int = Query(0, ge=0, description="Número de items a saltar"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de items a retornar")
):
    """
    Obtener items por categoría:
    
    - **category_id**: ID de la categoría
    - **available_only**: Solo items disponibles (True por defecto)
    - **skip**: Número de items a saltar (paginación)
    - **limit**: Número máximo de items a retornar
    
    No requiere autenticación.
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(category_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de categoría inválido"
            )
        
        # Verificar que la categoría existe
        category = await Category.get(PydanticObjectId(category_id))
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada"
            )
        
        # Construir filtros
        filters = {"category_id": PydanticObjectId(category_id)}
        if available_only:
            filters["available"] = True
        
        # Obtener items
        items = await MenuItem.find(filters).skip(skip).limit(limit).to_list()
        
        # Contar total
        total = await MenuItem.find(filters).count()
        
        # Convertir a respuesta
        item_responses = [
            MenuItemResponse(
                id=str(item.id),
                category_id=str(item.category_id),
                name=item.name,
                description=item.description,
                price=item.price,
                image_url=item.image_url,
                available=item.available,
                created_at=item.created_at,
                updated_at=item.updated_at
            ) for item in items
        ]
        
        return MenuItemList(
            items=item_responses,
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener items de la categoría: {str(e)}"
        )