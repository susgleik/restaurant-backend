from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi import status  # Import específico y correcto
from typing import Optional, List
from beanie import PydanticObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from bson import Decimal128

from app.schemas.order import (
    OrderCreate,
    OrderUpdate,
    OrderResponse,
    OrderList,
    OrderWithUserInfo,
    OrderStatusUpdate,
    OrderStats,
    OrderItemResponse
)
from app.models.order import Order, OrderItem, OrderStatus
from app.models.menu_item import MenuItem
from app.models.cart_item import CartItem
from app.models.user import User
from app.core.deps import get_current_admin_user
from app.core.security import get_current_active_user

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.get(
    "/",
    response_model=OrderList,
    summary="Obtener pedidos",
    description="Obtener lista de pedidos con filtros opcionales"
)
async def get_orders(
    order_status: Optional[OrderStatus] = Query(None, alias="status", description="Filtrar por estado"),
    user_id: Optional[str] = Query(None, description="Filtrar por usuario (solo ADMIN_STAFF)"),
    date_from: Optional[datetime] = Query(None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta"),
    min_total: Optional[Decimal] = Query(None, ge=0, description="Total mínimo"),
    max_total: Optional[Decimal] = Query(None, ge=0, description="Total máximo"),
    skip: int = Query(0, ge=0, description="Número de pedidos a saltar"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de pedidos a retornar"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener lista de pedidos con filtros opcionales.
    Los clientes solo ven sus propios pedidos.
    Los ADMIN_STAFF pueden ver todos los pedidos.
    """
    try:
        # Construir filtros
        filters = {}
        
        # Los clientes solo pueden ver sus propios pedidos
        if current_user.role == "CLIENT":
            filters["user_id"] = current_user.id
        elif user_id and current_user.role == "ADMIN_STAFF":
            # Solo ADMIN_STAFF puede filtrar por user_id específico
            if not PydanticObjectId.is_valid(user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID de usuario inválido"
                )
            filters["user_id"] = PydanticObjectId(user_id)
        
        if order_status:
            filters["status"] = order_status
        
        if date_from or date_to:
            date_filter = {}
            if date_from:
                date_filter["$gte"] = date_from
            if date_to:
                date_filter["$lte"] = date_to
            filters["created_at"] = date_filter
        
        if min_total is not None or max_total is not None:
            total_filter = {}
            if min_total is not None:
                total_filter["$gte"] = min_total
            if max_total is not None:
                total_filter["$lte"] = max_total
            filters["total"] = total_filter
        
        # Obtener pedidos con paginación
        orders = await Order.find(filters).skip(skip).limit(limit).sort(-Order.created_at).to_list()
        
        # Contar total
        total = await Order.find(filters).count()
        
        # Convertir a respuesta
        order_responses = await _convert_orders_to_response(orders)
        
        return OrderList(
            orders=order_responses,
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener pedidos: {str(e)}"
        )

@router.get(
    "/{order_id}",
    response_model=OrderWithUserInfo,
    summary="Obtener pedido por ID",
    description="Obtener información detallada de un pedido específico"
)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener pedido por ID con información del usuario si es admin.
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(order_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de pedido inválido"
            )
        
        # Buscar pedido
        order = await Order.get(PydanticObjectId(order_id))
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado"
            )
        
        # Verificar permisos
        if current_user.role == "CLIENT" and order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para ver este pedido"
            )
        
        # Obtener información del usuario si es ADMIN_STAFF
        user_info = {}
        if current_user.role == "ADMIN_STAFF":
            user = await User.get(order.user_id)
            if user:
                user_info = {
                    "username": user.username,
                    "user_email": user.email
                }
        
        # Convertir items
        items_response = await _convert_order_items_to_response(order.items)
        
        # Manejar total
        total = order.total
        if isinstance(total, Decimal128):
            total = Decimal(str(total.to_decimal()))
        
        return OrderWithUserInfo(
            id=str(order.id),
            user_id=str(order.user_id),
            items=items_response,
            total=total,
            status=order.status,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at,
            **user_info
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener pedido: {str(e)}"
        )

@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo pedido",
    description="Crear un nuevo pedido especificando items manualmente"
)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Crear nuevo pedido especificando items manualmente.
    Usa los precios actuales de los items del menú.
    """
    try:
        # Validar que hay items
        if not order_data.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El pedido debe tener al menos un item"
            )
        
        # Validar y obtener información de los items
        order_items = []
        total = Decimal('0.00')
        
        for item_data in order_data.items:
            # Validar ObjectId del menu item
            if not PydanticObjectId.is_valid(item_data.menu_item_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"ID de item del menú inválido: {item_data.menu_item_id}"
                )
            
            # Obtener item del menú
            menu_item = await MenuItem.get(PydanticObjectId(item_data.menu_item_id))
            if not menu_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item del menú no encontrado: {item_data.menu_item_id}"
                )
            
            # Verificar disponibilidad
            if not menu_item.available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El item '{menu_item.name}' no está disponible"
                )
            
            # Calcular subtotal con precio actual
            subtotal = menu_item.price * item_data.quantity
            total += subtotal
            
            # Crear OrderItem
            order_item = OrderItem(
                menu_item_id=menu_item.id,
                menu_item_name=menu_item.name,
                quantity=item_data.quantity,
                unit_price=menu_item.price,
                subtotal=subtotal,
                special_instructions=item_data.special_instructions
            )
            order_items.append(order_item)
        
        # Crear pedido
        order = Order(
            user_id=current_user.id,
            items=order_items,
            total=total,
            notes=order_data.notes
        )
        
        # Guardar en la base de datos
        await order.save()
        
        # Convertir respuesta
        items_response = await _convert_order_items_to_response(order.items)
        
        return OrderResponse(
            id=str(order.id),
            user_id=str(order.user_id),
            items=items_response,
            total=order.total,
            status=order.status,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear pedido: {str(e)}"
        )

@router.post(
    "/from-cart",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido desde el carrito",
    description="Crear un nuevo pedido con todos los items del carrito del usuario"
)
async def create_order_from_cart(
    notes: Optional[str] = Query(None, max_length=500, description="Notas adicionales del pedido"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Crear pedido desde el carrito del usuario.
    
    - Valida que el carrito no esté vacío
    - Verifica disponibilidad de todos los items
    - Usa precios actuales (no los guardados en el carrito)
    - Limpia el carrito después de crear el pedido exitosamente
    """
    try:
        # Obtener items del carrito
        cart_items = await CartItem.find({"user_id": current_user.id}).to_list()
        
        if not cart_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El carrito está vacío. Agrega items antes de hacer el pedido."
            )
        
        # Validar y convertir items del carrito a items del pedido
        order_items = []
        total = Decimal('0.00')
        unavailable_items = []
        
        for cart_item in cart_items:
            # Obtener item del menú para verificar disponibilidad y precio actual
            menu_item = await MenuItem.get(cart_item.menu_item_id)
            
            if not menu_item:
                # Item del menú ya no existe, eliminar del carrito
                await cart_item.delete()
                unavailable_items.append(f"{cart_item.menu_item_name} (eliminado del menú)")
                continue
            
            # Verificar disponibilidad
            if not menu_item.available:
                unavailable_items.append(f"{menu_item.name} (no disponible)")
                continue
            
            # Usar precio ACTUAL del menú, no el guardado en el carrito
            current_price = menu_item.price
            subtotal = current_price * cart_item.quantity
            total += subtotal
            
            # Crear OrderItem con precio actual
            order_item = OrderItem(
                menu_item_id=menu_item.id,
                menu_item_name=menu_item.name,
                quantity=cart_item.quantity,
                unit_price=current_price,
                subtotal=subtotal,
                special_instructions=None  # Los cart_items no tienen instrucciones especiales por ahora
            )
            order_items.append(order_item)
        
        # Si hay items no disponibles, informar al usuario
        if unavailable_items:
            if not order_items:  # Si TODOS los items no están disponibles
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ningún item del carrito está disponible: {', '.join(unavailable_items)}"
                )
            else:  # Si ALGUNOS items no están disponibles, continuar pero informar
                # Aquí podrías log o notificar, pero continúas con los items disponibles
                pass
        
        # Validar que queden items para el pedido
        if not order_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay items disponibles para crear el pedido"
            )
        
        # Crear pedido
        order = Order(
            user_id=current_user.id,
            items=order_items,
            total=total,
            notes=notes
        )
        
        # Guardar en la base de datos
        await order.save()
        
        # Limpiar carrito SOLO después de crear el pedido exitosamente
        await CartItem.find({"user_id": current_user.id}).delete()
        
        # Convertir respuesta
        items_response = await _convert_order_items_to_response(order.items)
        
        return OrderResponse(
            id=str(order.id),
            user_id=str(order.user_id),
            items=items_response,
            total=order.total,
            status=order.status,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear pedido desde carrito: {str(e)}"
        )

@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Actualizar estado del pedido",
    description="Actualizar el estado de un pedido (solo ADMIN_STAFF)"
)
async def update_order_status(
    order_id: str,
    status_data: OrderStatusUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar estado del pedido con validación de transiciones válidas.
    Solo ADMIN_STAFF puede cambiar el estado de los pedidos.
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(order_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de pedido inválido"
            )
        
        # Buscar pedido
        order = await Order.get(PydanticObjectId(order_id))
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado"
            )
        
        # Validar transición de estado
        current_status = order.status
        new_status = status_data.status
        
        # Evitar cambios innecesarios
        if current_status == new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El pedido ya está en estado {new_status}"
            )
        
        # Lógica de transiciones válidas
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED],
            OrderStatus.IN_PREPARATION: [OrderStatus.READY, OrderStatus.CANCELLED],
            OrderStatus.READY: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
            OrderStatus.DELIVERED: [],  # Estado final
            OrderStatus.CANCELLED: []   # Estado final
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede cambiar el estado de {current_status} a {new_status}"
            )
        
        # Actualizar estado
        order.status = new_status
        order.updated_at = datetime.utcnow()
        await order.save()
        
        # Convertir respuesta
        items_response = await _convert_order_items_to_response(order.items)
        
        # Manejar total
        total = order.total
        if isinstance(total, Decimal128):
            total = Decimal(str(total.to_decimal()))
        
        return OrderResponse(
            id=str(order.id),
            user_id=str(order.user_id),
            items=items_response,
            total=total,
            status=order.status,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar estado del pedido: {str(e)}"
        )

# ===== FUNCIONES AUXILIARES =====

async def _convert_order_items_to_response(order_items: List[OrderItem]) -> List[OrderItemResponse]:
    """Convierte lista de OrderItem a OrderItemResponse manejando Decimal128"""
    items_response = []
    for item in order_items:
        # Manejar conversión de Decimal128 si es necesario
        unit_price = item.unit_price
        subtotal = item.subtotal
        
        if isinstance(unit_price, Decimal128):
            unit_price = Decimal(str(unit_price.to_decimal()))
        if isinstance(subtotal, Decimal128):
            subtotal = Decimal(str(subtotal.to_decimal()))
        
        items_response.append(OrderItemResponse(
            menu_item_id=str(item.menu_item_id),
            menu_item_name=item.menu_item_name,
            quantity=item.quantity,
            unit_price=unit_price,
            subtotal=subtotal,
            special_instructions=item.special_instructions
        ))
    return items_response

async def _convert_orders_to_response(orders: List[Order]) -> List[OrderResponse]:
    """Convierte lista de Order a OrderResponse"""
    order_responses = []
    for order in orders:
        items_response = await _convert_order_items_to_response(order.items)
        
        # Manejar conversión de total si es necesario
        total = order.total
        if isinstance(total, Decimal128):
            total = Decimal(str(total.to_decimal()))
        
        order_responses.append(OrderResponse(
            id=str(order.id),
            user_id=str(order.user_id),
            items=items_response,
            total=total,
            status=order.status,
            notes=order.notes,
            created_at=order.created_at,
            updated_at=order.updated_at
        ))
    return order_responses  


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancelar pedido",
    description="Cancelar un pedido (cambiar estado a CANCELLED)"
)
async def cancel_order(
    order_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancelar pedido con validaciones de estado y permisos.
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(order_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de pedido inválido"
            )
        
        # Buscar pedido
        order = await Order.get(PydanticObjectId(order_id))
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado"
            )
        
        # Verificar si ya está cancelado o entregado
        if order.status == OrderStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El pedido ya está cancelado"
            )
        
        if order.status == OrderStatus.DELIVERED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede cancelar un pedido ya entregado"
            )
        
        # Verificar permisos
        if current_user.role == "CLIENT":
            # Los clientes solo pueden cancelar sus propios pedidos
            if order.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para cancelar este pedido"
                )
            
            # Los clientes solo pueden cancelar pedidos PENDING
            if order.status != OrderStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solo se pueden cancelar pedidos en estado PENDING"
                )
        
        # Cancelar pedido
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        await order.save()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cancelar pedido: {str(e)}"
        )
        
@router.get(
    "/stats/dashboard",
    response_model=OrderStats,
    summary="Obtener estadísticas de pedidos",
    description="Obtener estadísticas generales de pedidos (solo ADMIN_STAFF)"
)
async def get_order_stats(
    date_from: Optional[datetime] = Query(None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener estadísticas de pedidos para dashboard administrativo.
    """
    try:
        # Establecer fechas por defecto si no se proporcionan
        if not date_to:
            date_to = datetime.utcnow()
        if not date_from:
            date_from = date_to - timedelta(days=30)
        
        # Filtros de fecha
        date_filter = {
            "created_at": {
                "$gte": date_from,
                "$lte": date_to
            }
        }
        
        # Obtener todas las órdenes en el rango de fechas
        orders = await Order.find(date_filter).to_list()
        
        # Calcular estadísticas
        total_orders = len(orders)
        pending_orders = len([o for o in orders if o.status == OrderStatus.PENDING])
        in_preparation_orders = len([o for o in orders if o.status == OrderStatus.IN_PREPARATION])
        ready_orders = len([o for o in orders if o.status == OrderStatus.READY])
        delivered_orders = len([o for o in orders if o.status == OrderStatus.DELIVERED])
        cancelled_orders = len([o for o in orders if o.status == OrderStatus.CANCELLED])
        
        # Calcular ingresos (solo pedidos entregados)
        delivered_order_totals = [o.total for o in orders if o.status == OrderStatus.DELIVERED]
        total_revenue = sum(delivered_order_totals) if delivered_order_totals else Decimal('0.00')
        average_order_value = total_revenue / len(delivered_order_totals) if delivered_order_totals else Decimal('0.00')
        
        return OrderStats(
            total_orders=total_orders,
            pending_orders=pending_orders,
            in_preparation_orders=in_preparation_orders,
            ready_orders=ready_orders,
            delivered_orders=delivered_orders,
            cancelled_orders=cancelled_orders,
            total_revenue=total_revenue,
            average_order_value=average_order_value
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )