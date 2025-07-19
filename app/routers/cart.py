from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, List
from beanie import PydanticObjectId
from datetime import datetime, timedelta
from decimal import Decimal

from app.schemas.cart import (
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse,
    CartItemWithMenuInfo,
    CartSummary,
    BulkCartUpdate,
    CartStats,
    CartItemQuickAdd
)
from app.models.cart_item import CartItem
from app.models.menu_item import MenuItem
from app.models.category import Category
from app.models.user import User
from app.core.deps import get_current_admin_user
from app.core.security import get_current_active_user

router = APIRouter(prefix="/cart", tags=["Cart"])

@router.get(
    "/",
    response_model=CartSummary,
    summary="Obtener carrito del usuario",
    description="Obtener todos los items del carrito del usuario autenticado con información completa"
)
async def get_cart(
    include_unavailable: bool = Query(False, description="Incluir items no disponibles"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener carrito completo del usuario:
    
    - **include_unavailable**: Incluir items que ya no están disponibles
    
    Incluye información detallada de cada item del menú y cálculos de totales.
    """
    try:
        # Obtener items del carrito
        cart_items = await CartItem.find({"user_id": current_user.id}).to_list()
        
        if not cart_items:
            return CartSummary(
                items=[],
                total_items=0,
                total_quantity=0,
                subtotal=Decimal('0.00'),
                estimated_tax=Decimal('0.00'),
                estimated_total=Decimal('0.00'),
                is_empty=True,
                last_updated=None
            )
        
        # Obtener información detallada de cada item
        detailed_items = []
        total_quantity = 0
        subtotal = Decimal('0.00')
        
        for cart_item in cart_items:
            # Obtener información del menu item
            menu_item = await MenuItem.get(cart_item.menu_item_id)
            
            # Si el item no existe o no está disponible, decidir qué hacer
            if not menu_item:
                if include_unavailable:
                    # Crear respuesta con info limitada
                    detailed_item = CartItemWithMenuInfo(
                        id=str(cart_item.id),
                        user_id=str(cart_item.user_id),
                        menu_item_id=str(cart_item.menu_item_id),
                        menu_item_name=cart_item.menu_item_name + " (No disponible)",
                        menu_item_description="Este item ya no está disponible",
                        menu_item_price=cart_item.menu_item_price,
                        menu_item_image_url=None,
                        menu_item_available=False,
                        category_name=None,
                        quantity=cart_item.quantity,
                        subtotal=cart_item.subtotal,
                        created_at=cart_item.created_at,
                        updated_at=cart_item.updated_at
                    )
                    detailed_items.append(detailed_item)
                continue
            
            # Obtener información de la categoría
            category = await Category.get(menu_item.category_id) if menu_item else None
            
            # Si el item no está disponible y no se quieren incluir, saltar
            if not menu_item.available and not include_unavailable:
                continue
            
            # Crear respuesta detallada
            detailed_item = CartItemWithMenuInfo(
                id=str(cart_item.id),
                user_id=str(cart_item.user_id),
                menu_item_id=str(cart_item.menu_item_id),
                menu_item_name=menu_item.name,
                menu_item_description=menu_item.description,
                menu_item_price=menu_item.price,  # Precio actual, no el guardado
                menu_item_image_url=menu_item.image_url,
                menu_item_available=menu_item.available,
                category_name=category.name if category else None,
                quantity=cart_item.quantity,
                subtotal=menu_item.price * cart_item.quantity,  # Recalcular con precio actual
                created_at=cart_item.created_at,
                updated_at=cart_item.updated_at
            )
            
            detailed_items.append(detailed_item)
            total_quantity += cart_item.quantity
            subtotal += detailed_item.subtotal
        
        # Calcular impuestos (puedes configurar el porcentaje)
        tax_rate = Decimal('0.10')  # 10% de impuesto
        estimated_tax = subtotal * tax_rate
        estimated_total = subtotal + estimated_tax
        
        # Encontrar la fecha de última actualización
        last_updated = max([item.updated_at for item in cart_items]) if cart_items else None
        
        return CartSummary(
            items=detailed_items,
            total_items=len(detailed_items),
            total_quantity=total_quantity,
            subtotal=subtotal,
            estimated_tax=estimated_tax,
            estimated_total=estimated_total,
            is_empty=len(detailed_items) == 0,
            last_updated=last_updated
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener carrito: {str(e)}"
        )

@router.post(
    "/items",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar item al carrito",
    description="Agregar un item al carrito o actualizar cantidad si ya existe"
)
async def add_to_cart(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Agregar item al carrito:
    
    - **menu_item_id**: ID del item del menú
    - **quantity**: Cantidad a agregar (se suma si el item ya existe)
    
    Si el item ya está en el carrito, se suma la cantidad.
    Si es un item nuevo, se crea una nueva entrada.
    """
    try:
        # Validar que el menu item existe
        if not PydanticObjectId.is_valid(item_data.menu_item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de item del menú inválido"
            )
        
        menu_item = await MenuItem.get(PydanticObjectId(item_data.menu_item_id))
        if not menu_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item del menú no encontrado"
            )
        
        # Verificar disponibilidad
        if not menu_item.available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El item '{menu_item.name}' no está disponible"
            )
        
        # Verificar si ya existe en el carrito
        existing_cart_item = await CartItem.find_one({
            "user_id": current_user.id,
            "menu_item_id": menu_item.id
        })
        
        if existing_cart_item:
            # Actualizar cantidad existente
            new_quantity = existing_cart_item.quantity + item_data.quantity
            
            # Validar cantidad máxima
            if new_quantity > 20:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cantidad máxima por item: 20"
                )
            
            existing_cart_item.quantity = new_quantity
            existing_cart_item.updated_at = datetime.utcnow()
            await existing_cart_item.save()
            
            return CartItemResponse(
                id=str(existing_cart_item.id),
                user_id=str(existing_cart_item.user_id),
                menu_item_id=str(existing_cart_item.menu_item_id),
                menu_item_name=existing_cart_item.menu_item_name,
                menu_item_price=existing_cart_item.menu_item_price,
                quantity=existing_cart_item.quantity,
                subtotal=existing_cart_item.subtotal,
                created_at=existing_cart_item.created_at,
                updated_at=existing_cart_item.updated_at
            )
        else:
            # Crear nuevo item en el carrito
            cart_item = CartItem(
                user_id=current_user.id,
                menu_item_id=menu_item.id,
                menu_item_name=menu_item.name,
                menu_item_price=menu_item.price,
                quantity=item_data.quantity
            )
            
            await cart_item.save()
            
            return CartItemResponse(
                id=str(cart_item.id),
                user_id=str(cart_item.user_id),
                menu_item_id=str(cart_item.menu_item_id),
                menu_item_name=cart_item.menu_item_name,
                menu_item_price=cart_item.menu_item_price,
                quantity=cart_item.quantity,
                subtotal=cart_item.subtotal,
                created_at=cart_item.created_at,
                updated_at=cart_item.updated_at
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agregar item al carrito: {str(e)}"
        )

@router.put(
    "/items/{cart_item_id}",
    response_model=CartItemResponse,
    summary="Actualizar cantidad de item en carrito",
    description="Actualizar la cantidad específica de un item en el carrito"
)
async def update_cart_item(
    cart_item_id: str,
    item_data: CartItemUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualizar cantidad de item en carrito:
    
    - **cart_item_id**: ID del item en el carrito
    - **quantity**: Nueva cantidad (reemplaza la cantidad actual)
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(cart_item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de item del carrito inválido"
            )
        
        # Buscar item del carrito
        cart_item = await CartItem.get(PydanticObjectId(cart_item_id))
        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item del carrito no encontrado"
            )
        
        # Verificar permisos
        if cart_item.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para modificar este item"
            )
        
        # Actualizar cantidad
        cart_item.quantity = item_data.quantity
        cart_item.updated_at = datetime.utcnow()
        await cart_item.save()
        
        return CartItemResponse(
            id=str(cart_item.id),
            user_id=str(cart_item.user_id),
            menu_item_id=str(cart_item.menu_item_id),
            menu_item_name=cart_item.menu_item_name,
            menu_item_price=cart_item.menu_item_price,
            quantity=cart_item.quantity,
            subtotal=cart_item.subtotal,
            created_at=cart_item.created_at,
            updated_at=cart_item.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar item del carrito: {str(e)}"
        )

@router.delete(
    "/items/{cart_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar item del carrito",
    description="Eliminar un item específico del carrito"
)
async def remove_cart_item(
    cart_item_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Eliminar item del carrito:
    
    - **cart_item_id**: ID del item en el carrito
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(cart_item_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de item del carrito inválido"
            )
        
        # Buscar item del carrito
        cart_item = await CartItem.get(PydanticObjectId(cart_item_id))
        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item del carrito no encontrado"
            )
        
        # Verificar permisos
        if cart_item.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para eliminar este item"
            )
        
        # Eliminar item
        await cart_item.delete()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar item del carrito: {str(e)}"
        )

@router.delete(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Limpiar carrito completo",
    description="Eliminar todos los items del carrito del usuario"
)
async def clear_cart(
    current_user: User = Depends(get_current_active_user)
):
    """
    Limpiar carrito completo:
    
    Elimina todos los items del carrito del usuario autenticado.
    """
    try:
        # Eliminar todos los items del carrito del usuario
        result = await CartItem.find({"user_id": current_user.id}).delete()
        
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al limpiar carrito: {str(e)}"
        )

@router.post(
    "/quick-add",
    response_model=CartItemResponse,
    summary="Agregar rápido al carrito",
    description="Agregar un item al carrito rápidamente (cantidad por defecto: 1)"
)
async def quick_add_to_cart(
    menu_item_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Agregar rápido al carrito:
    
    - **menu_item_id**: ID del item del menú
    
    Agrega 1 unidad del item al carrito. Si ya existe, suma 1 a la cantidad.
    """
    item_data = CartItemCreate(menu_item_id=menu_item_id, quantity=1)
    return await add_to_cart(item_data, current_user)

@router.post(
    "/bulk-update",
    response_model=CartSummary,
    summary="Actualización masiva del carrito",
    description="Actualizar múltiples items del carrito en una sola operación"
)
async def bulk_update_cart(
    bulk_data: BulkCartUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualización masiva del carrito:
    
    - **items**: Lista de items con sus cantidades
    
    Reemplaza completamente el contenido del carrito con los items especificados.
    """
    try:
        # Limpiar carrito actual
        await CartItem.find({"user_id": current_user.id}).delete()
        
        # Agregar nuevos items
        for item_data in bulk_data.items:
            await add_to_cart(item_data, current_user)
        
        # Retornar carrito actualizado
        return await get_cart(current_user=current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en actualización masiva del carrito: {str(e)}"
        )

@router.post(
    "/sync",
    response_model=CartSummary,
    summary="Sincronizar carrito",
    description="Sincronizar carrito con el servidor (útil para resolver conflictos)"
)
async def sync_cart(
    current_user: User = Depends(get_current_active_user)
):
    """
    Sincronizar carrito:
    
    Valida todos los items del carrito y actualiza precios/disponibilidad.
    Útil para sincronización después de estar offline.
    """
    try:
        # Obtener carrito actual
        cart_items = await CartItem.find({"user_id": current_user.id}).to_list()
        
        items_to_remove = []
        items_updated = False
        
        for cart_item in cart_items:
            # Verificar si el menu item aún existe
            menu_item = await MenuItem.get(cart_item.menu_item_id)
            
            if not menu_item:
                # Item no existe, marcar para eliminación
                items_to_remove.append(cart_item)
                continue
            
            # Actualizar información si ha cambiado
            if (cart_item.menu_item_name != menu_item.name or 
                cart_item.menu_item_price != menu_item.price):
                cart_item.menu_item_name = menu_item.name
                cart_item.menu_item_price = menu_item.price
                cart_item.updated_at = datetime.utcnow()
                await cart_item.save()
                items_updated = True
        
        # Eliminar items que ya no existen
        for item in items_to_remove:
            await item.delete()
        
        # Retornar carrito sincronizado
        return await get_cart(current_user=current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al sincronizar carrito: {str(e)}"
        )

@router.get(
    "/stats",
    response_model=CartStats,
    summary="Estadísticas del carrito",
    description="Obtener estadísticas generales de carritos (solo ADMIN_STAFF)"
)
async def get_cart_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Estadísticas del carrito:
    
    Solo ADMIN_STAFF puede acceder a estas estadísticas.
    """
    try:
        # Total de usuarios con items en carrito
        total_users_with_cart = await CartItem.distinct("user_id")
        total_users_count = len(total_users_with_cart)
        
        # Total de items en todos los carritos
        all_cart_items = await CartItem.find().to_list()
        total_cart_items = len(all_cart_items)
        
        # Valor promedio de carrito
        if total_users_count > 0:
            user_totals = {}
            for item in all_cart_items:
                user_id = str(item.user_id)
                if user_id not in user_totals:
                    user_totals[user_id] = Decimal('0.00')
                user_totals[user_id] += item.subtotal
            
            average_cart_value = sum(user_totals.values()) / len(user_totals)
        else:
            average_cart_value = Decimal('0.00')
        
        # Carritos abandonados en 24h (items no actualizados en 24h)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        abandoned_carts = await CartItem.find({
            "updated_at": {"$lt": yesterday}
        }).distinct("user_id")
        abandoned_carts_24h = len(abandoned_carts)
        
        # Item más agregado al carrito
        if all_cart_items:
            item_counts = {}
            for item in all_cart_items:
                name = item.menu_item_name
                if name not in item_counts:
                    item_counts[name] = 0
                item_counts[name] += item.quantity
            
            most_added_item = max(item_counts, key=item_counts.get) if item_counts else None
        else:
            most_added_item = None
        
        return CartStats(
            total_users_with_cart=total_users_count,
            total_cart_items=total_cart_items,
            average_cart_value=average_cart_value,
            abandoned_carts_24h=abandoned_carts_24h,
            most_added_item=most_added_item
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas del carrito: {str(e)}"
        )