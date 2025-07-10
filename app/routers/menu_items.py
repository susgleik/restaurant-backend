from fastapi import APIRouter, HTTPException, Depends, status, Query
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

router = APIRouter(prefix="/menu-items", tags=["Menu Items"])

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