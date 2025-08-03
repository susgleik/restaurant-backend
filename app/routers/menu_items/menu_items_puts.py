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
    
@router.put(
    "/{item_id}",
    response_model=MenuItemResponse,
    summary="Actualizar item del menú",
    description="Actualizar un item del menú existente (solo ADMIN_STAFF)"
)
async def update_menu_item(
    item_id: str,
    item_data: MenuItemUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar item del menú:
    
    - **item_id**: ID único del item
    - **category_id**: Nuevo ID de categoría (opcional)
    - **name**: Nuevo nombre (opcional)
    - **description**: Nueva descripción (opcional)
    - **price**: Nuevo precio (opcional)
    - **image_url**: Nueva URL de imagen (opcional)
    - **available**: Nuevo estado de disponibilidad (opcional)
    
    Requiere autenticación con rol ADMIN_STAFF.
    """
    try:
        # Validar ObjectId del item
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
        
        # Validar nueva categoría si se proporciona
        if item_data.category_id:
            if not PydanticObjectId.is_valid(item_data.category_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID de categoría inválido"
                )
            
            category = await Category.get(PydanticObjectId(item_data.category_id))
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Categoría no encontrada"
                )
            
            if not category.active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede mover un item a una categoría inactiva"
                )
        
        # Verificar si el nuevo nombre ya existe en la categoría
        if item_data.name and item_data.name != item.name:
            category_id_to_check = PydanticObjectId(item_data.category_id) if item_data.category_id else item.category_id
            existing_item = await MenuItem.find_one({
                "category_id": category_id_to_check,
                "name": item_data.name,
                "_id": {"$ne": item.id}
            })
            if existing_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe un item con este nombre en esta categoría"
                )
        
        # Actualizar campos
        update_data = item_data.dict(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                if field == "category_id":
                    setattr(item, field, PydanticObjectId(value))
                else:
                    setattr(item, field, value)
            
            # Actualizar timestamp
            item.updated_at = datetime.utcnow()
            
            # Guardar cambios
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
            detail=f"Error al actualizar item del menú: {str(e)}"
        )