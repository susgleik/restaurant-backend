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
     
@router.post(
    "/",
    response_model=MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo item del menú",
    description="Crear un nuevo item del menú (solo ADMIN_STAFF)"
)
async def create_menu_item(
    item_data: MenuItemCreate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Crear nuevo item del menú:
    
    - **category_id**: ID de la categoría
    - **name**: Nombre del item (2-100 caracteres)
    - **description**: Descripción opcional (máximo 500 caracteres)
    - **price**: Precio del item (mayor que 0)
    - **image_url**: URL de la imagen (opcional)
    - **available**: Si el item está disponible (True por defecto)
    
    Requiere autenticación con rol ADMIN_STAFF.
    """
    try:
        # Validar que la categoría existe
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
                detail="No se puede crear un item en una categoría inactiva"
            )
        
        # Verificar si ya existe un item con el mismo nombre en la categoría
        existing_item = await MenuItem.find_one({
            "category_id": PydanticObjectId(item_data.category_id),
            "name": item_data.name
        })
        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un item con este nombre en esta categoría"
            )
        
        # Crear nuevo item
        item = MenuItem(
            category_id=PydanticObjectId(item_data.category_id),
            name=item_data.name,
            description=item_data.description,
            price=item_data.price,
            image_url=item_data.image_url,
            available=item_data.available
        )
        
        # Guardar en la base de datos
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
            detail=f"Error al crear item del menú: {str(e)}"
        )
        
# create image processor instance if using Azure
@router.post(
    "/upload_image",
    summary="upload image for menu item",
    description="Upload an image for a menu item. Requires authentication (only admin/staff).",
)
async def upload_menu_item_image(
    File: UploadFile = File(..., description="Image file to upload"),
    current_user: User = Depends(get_current_admin_user)
):
    """ 
    Upload an image for a menu item.
    
    - file: Image file to upload (JPG, PNG, WEBP, GIF)
    - max file size configured in settings 
    
    ADMIN_STAFF authentication required.
    
    Returns the URL of the uploaded image.
    """
    
    try:
        if not settings.use_azure_storage:
            raise HTTPException(
                status_code=501,
                detail="File upload is not supported in this configuration. Please use Azure Storage."
            )
        
        processor = AzureImageProcessor()
        
        try:
            image_url = await processor.upload_image(file=File)
            
            return {
                "success": True,
                "message": "Image uploaded successfully",
                "image_url": image_url,
                "filename": image_url.split("/")[-1]
            }
        finally:
            await processor.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )