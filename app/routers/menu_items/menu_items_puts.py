from fastapi import APIRouter, HTTPException, Depends, status, Query, File, UploadFile, Form
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
        
@router.put(
    "/{item_id}/update-with-image",
    response_model=MenuItemResponse,
    
)
async def update_menu_item_with_image(
    item_id: str,
    category_id: Optional[str] = Form(None, description="Nuevo ID de la categoría"),
    name: Optional[str] = Form(None, min_length=2, max_length=100, description="Nuevo nombre del item"),
    description: Optional[str] = Form(None, max_length=500, description="Nueva descripción del item"),
    price: Optional[Decimal] = Form(None, gt=0, description="Nuevo precio del item"),
    available: Optional[bool] = Form(None, description="Nueva disponibilidad del item"),
    image: UploadFile = File(None, description="Nueva imagen del item (opcional)"),
    
    # Flag para eliminar imagen actual
    remove_image: bool = Form(False, description="Eliminar imagen actual del item"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar item del menú con imagen:
    
    - item_id: ID único del item
    - category_id: Nuevo ID de categoría (opcional)
    - name: Nuevo nombre (opcional)
    - description: Nueva descripción (opcional)  
    - price: Nuevo precio (opcional)
    - available: Nueva disponibilidad (opcional)
    - image: Nueva imagen (opcional)
    - remove_image**: Eliminar imagen actual (opcional)
    
    Requiere autenticación con rol ADMIN_STAFF.
    """
    
    processor = None
    image_url = None
    old_image_url = None
    
    try:
        
        if not PydanticObjectId.is_valid(item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de item inválido"
            )
        # search item
        item = await MenuItem.get(PydanticObjectId(item_id))
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item del menú no encontrado"
            )
        
        old_image_url = item.image_url
        
        # check if category_id is provided
        if category_id:
            if not PydanticObjectId.is_valid(category_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID de categoría inválido"
                )
            category = await Category.get(PydanticObjectId(category_id))
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
        
        # check if item with same name exists in category
        if name and name != item.name:
            category_id_to_check = PydanticObjectId(category_id) if category_id else item.category_id
            existing_item = await MenuItem.find_one({
                "category_id": category_id_to_check,
                "name": name,
                "_id": {"$ne": item.id} 
            })
            if existing_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe un item con este nombre en esta categoría"
                )
        
        # image processing
        if image and image.filename:
            # upload new image 
            if not settings.use_azure_storage:
                raise HTTPException(
                    status_code=501,
                    detail="File upload is not supported in this configuration. Please use Azure Storage."
                )    
            
            processor = AzureImageProcessor()
            new_image_url = await processor.upload_image(image, folder="menu-items")
        elif remove_image:
                # Eliminar imagen actual
            new_image_url = None
        
        # Actualizar campos
        if category_id:
            item.category_id = PydanticObjectId(category_id)
        if name:
            item.name = name
        if description is not None:  # Permitir string vacío
            item.description = description
        if price:
            item.price = price
        if available is not None:
            item.available = available
        if new_image_url is not None or remove_image:
            item.image_url = new_image_url
        
        # Actualizar timestamp
        item.updated_at = datetime.utcnow()
        
        # Guardar cambios
        await item.save()
        
        # Eliminar imagen anterior si se cambió
        if (new_image_url or remove_image) and old_image_url and processor:
            try:
                await processor.delete_image(old_image_url)
            except:
                pass  # Si no se puede eliminar la imagen anterior, no fallar
        
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
        # if exists an error, delete the new image if it was uploaded
        if new_image_url and processor:
            try:
                await processor.delete_image(new_image_url)
            except:
                pass  # Si no se puede eliminar la nueva imagen, no fallar
        raise  
    except Exception as e:
        # if exists an error, delete the new image if it was uploaded
        if new_image_url and processor:
            try:
                await processor.delete_image(new_image_url)
            except:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar item del menú: {str(e)}"
        )
    finally:
        if processor:
            await processor.close()   
            