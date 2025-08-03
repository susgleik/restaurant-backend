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


@router.delete(
    "delete-image/",
    summary="Delete image for menu item",
    description="Delete an image for a menu item by its filename. Requires authentication (only admin/staff).",
)
async def delete_menu_item_image(
    image_url: str = Query(..., description="URL of the image to delete"),
    current_user: User = Depends(get_current_admin_user)
):
    """ 
    delete an image by its URL.
    - image_url: use the full URL of the image to delete. 
    
    ADMIN_STAFF authentication required.
    """
    try: 
        if not settings.use_azure_storage:
            raise HTTPException(
                status_code=501,
                detail="File deletion is not supported in this configuration. Please use Azure Storage."
            )
            
            processor = AzureImageProcessor()
            
        try:
            success = await processor.delete_image(image_url)
            if success:
                return {
                    "success": True,
                    "message": "Image deleted successfully"
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail="Image not found"
                )
        finally:
            await processor.close()
            
    except HTTPException:
        raise   
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting image: {str(e)}"
        )

@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar item del menú",
    description="Eliminar un item del menú existente (solo ADMIN_STAFF)"
)
async def delete_menu_item(
    item_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar item del menú:
    
    - **item_id**: ID único del item
    
    Requiere autenticación con rol ADMIN_STAFF.
    
    Nota: No se puede eliminar un item que esté en pedidos activos o carritos.
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
        
        # Verificar si está en carritos activos
        from app.models.cart_item import CartItem
        cart_items_count = await CartItem.find({"menu_item_id": item.id}).count()
        if cart_items_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede eliminar el item porque está en {cart_items_count} carritos"
            )
        
        # Verificar si está en pedidos activos
        from app.models.order import Order
        active_orders = await Order.find({
            "items.menu_item_id": item.id,
            "status": {"$in": ["PENDING", "IN_PREPARATION", "READY"]}
        }).count()
        if active_orders > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede eliminar el item porque está en {active_orders} pedidos activos"
            )
        
        # Eliminar item
        await item.delete()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar item del menú: {str(e)}"
        )