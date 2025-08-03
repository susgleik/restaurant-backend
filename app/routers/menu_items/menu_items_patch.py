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

router = APIRouter(prefix="/menu-items", tags=["Menu Items"])

# import azure dependencies if using Azure
if settings.use_azure_storage:
    from app.utils.azure_image_utils import AzureImageProcessor

@router.patch(
    "/{item_id}/availability",
    response_model=MenuItemResponse,
    summary="Cambiar disponibilidad del item",
    description="Cambiar solo la disponibilidad de un item (solo ADMIN_STAFF)"
)
async def toggle_item_availability(
    item_id: str,
    available: bool,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cambiar disponibilidad del item:
    
    - **item_id**: ID único del item
    - **available**: Nueva disponibilidad (True/False)
    
    Requiere autenticación con rol ADMIN_STAFF.
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
        
        # Actualizar disponibilidad
        item.available = available
        item.updated_at = datetime.utcnow()
        await item.save()
        
        return MenuItemResponse(
            id=str(item.id),
            category_id=str(item.category_id),
            name=item.name,
            description=item.description,
            price=item.price,
            image_url=item.image_url,
            available=item.available,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar disponibilidad del item: {str(e)}"
        )