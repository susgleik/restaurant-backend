from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional, List
from beanie import PydanticObjectId
from datetime import datetime, timedelta
from decimal import Decimal

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
    status: Optional[OrderStatus] = Query(None, description="Filtrar por estado"),
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
    Obtener lista de pedidos:
    
    - **status**: Filtrar por estado del pedido
    - **user_id**: Filtrar por usuario (solo ADMIN_STAFF puede ver todos los pedidos)
    - **date_from**: Fecha desde (formato ISO)
    - **date_to**: Fecha hasta (formato ISO)
    - **min_total**: Total mínimo del pedido
    - **max_total**: Total máximo del pedido
    - **skip**: Número de pedidos a saltar (paginación)
    - **limit**: Número máximo de pedidos a retornar
    
    Los clientes solo pueden ver sus propios pedidos.
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
        
        if status:
            filters["status"] = status
        
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
        order_responses = []
        for order in orders:
            items_response = [
                OrderItemResponse(
                    menu_item_id=str(item.menu_item_id),
                    menu_item_name=item.menu_item_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                    special_instructions=item.special_instructions
                ) for item in order.items
            ]
            
            order_responses.append(OrderResponse(
                id=str(order.id),
                user_id=str(order.user_id),
                items=items_response,
                total=order.total,
                status=order.status,
                notes=order.notes,
                created_at=order.created_at,
                updated_at=order.updated_at
            ))
        
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
    Obtener pedido por ID:
    
    - **order_id**: ID único del pedido
    
    Los clientes solo pueden ver sus propios pedidos.
    Los ADMIN_STAFF pueden ver cualquier pedido.
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
        items_response = [
            OrderItemResponse(
                menu_item_id=str(item.menu_item_id),
                menu_item_name=item.menu_item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                special_instructions=item.special_instructions
            ) for item in order.items
        ]
        
        return OrderWithUserInfo(
            id=str(order.id),
            user_id=str(order.user_id),
            items=items_response,
            total=order.total,
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
    description="Crear un nuevo pedido desde los items del carrito o especificados"
)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Crear nuevo pedido:
    
    - **items**: Lista de items con cantidades e instrucciones especiales
    - **notes**: Notas adicionales del pedido (opcional)
    
    El pedido se crea con los precios actuales de los items del menú.
    Solo se pueden agregar items disponibles.
    """
    try:
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
            
            # Calcular subtotal
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
        
        # Limpiar carrito del usuario después de crear el pedido
        from app.models.cart_item import CartItem
        await CartItem.find({"user_id": current_user.id}).delete()
        
        # Convertir respuesta
        items_response = [
            OrderItemResponse(
                menu_item_id=str(item.menu_item_id),
                menu_item_name=item.menu_item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                special_instructions=item.special_instructions
            ) for item in order.items
        ]
        
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
    Actualizar estado del pedido:
    
    - **order_id**: ID único del pedido
    - **status**: Nuevo estado del pedido
    
    Solo ADMIN_STAFF puede cambiar el estado de los pedidos.
    
    Estados válidos:
    - PENDING: Pedido pendiente
    - IN_PREPARATION: En preparación
    - READY: Listo para entregar
    - DELIVERED: Entregado
    - CANCELLED: Cancelado
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
        items_response = [
            OrderItemResponse(
                menu_item_id=str(item.menu_item_id),
                menu_item_name=item.menu_item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                special_instructions=item.special_instructions
            ) for item in order.items
        ]
        
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
            detail=f"Error al actualizar estado del pedido: {str(e)}"
        )

@router.put(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Actualizar pedido",
    description="Actualizar notas y estado de un pedido"
)
async def update_order(
    order_id: str,
    order_data: OrderUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualizar pedido:
    
    - **order_id**: ID único del pedido
    - **status**: Nuevo estado (opcional, solo ADMIN_STAFF)
    - **notes**: Nuevas notas (opcional)
    
    Los clientes solo pueden actualizar las notas de sus pedidos en estado PENDING.
    Los ADMIN_STAFF pueden actualizar cualquier campo de cualquier pedido.
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
        if current_user.role == "CLIENT":
            # Los clientes solo pueden editar sus propios pedidos
            if order.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para editar este pedido"
                )
            
            # Los clientes solo pueden editar pedidos en estado PENDING
            if order.status != OrderStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solo se pueden editar pedidos en estado PENDING"
                )
            
            # Los clientes no pueden cambiar el estado
            if order_data.status is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Los clientes no pueden cambiar el estado del pedido"
                )
        
        # Actualizar campos
        update_data = order_data.dict(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                setattr(order, field, value)
            
            # Actualizar timestamp
            order.updated_at = datetime.utcnow()
            
            # Guardar cambios
            await order.save()
        
        # Convertir respuesta
        items_response = [
            OrderItemResponse(
                menu_item_id=str(item.menu_item_id),
                menu_item_name=item.menu_item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                special_instructions=item.special_instructions
            ) for item in order.items
        ]
        
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
            detail=f"Error al actualizar pedido: {str(e)}"
        )

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
    Cancelar pedido:
    
    - **order_id**: ID único del pedido
    
    Los clientes pueden cancelar sus propios pedidos si están en estado PENDING.
    Los ADMIN_STAFF pueden cancelar cualquier pedido que no esté DELIVERED.
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
    "/user/{user_id}",
    response_model=OrderList,
    summary="Obtener pedidos de un usuario",
    description="Obtener todos los pedidos de un usuario específico (solo ADMIN_STAFF)"
)
async def get_user_orders(
    user_id: str,
    status: Optional[OrderStatus] = Query(None, description="Filtrar por estado"),
    skip: int = Query(0, ge=0, description="Número de pedidos a saltar"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de pedidos a retornar"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener pedidos de un usuario:
    
    - **user_id**: ID del usuario
    - **status**: Filtrar por estado (opcional)
    - **skip**: Número de pedidos a saltar (paginación)
    - **limit**: Número máximo de pedidos a retornar
    
    Solo ADMIN_STAFF puede acceder a esta función.
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de usuario inválido"
            )
        
        # Verificar que el usuario existe
        user = await User.get(PydanticObjectId(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Construir filtros
        filters = {"user_id": PydanticObjectId(user_id)}
        if status:
            filters["status"] = status
        
        # Obtener pedidos
        orders = await Order.find(filters).skip(skip).limit(limit).sort(-Order.created_at).to_list()
        
        # Contar total
        total = await Order.find(filters).count()
        
        # Convertir a respuesta
        order_responses = []
        for order in orders:
            items_response = [
                OrderItemResponse(
                    menu_item_id=str(item.menu_item_id),
                    menu_item_name=item.menu_item_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                    special_instructions=item.special_instructions
                ) for item in order.items
            ]
            
            order_responses.append(OrderResponse(
                id=str(order.id),
                user_id=str(order.user_id),
                items=items_response,
                total=order.total,
                status=order.status,
                notes=order.notes,
                created_at=order.created_at,
                updated_at=order.updated_at
            ))
        
        return OrderList(
            orders=order_responses,
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener pedidos del usuario: {str(e)}"
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
    Obtener estadísticas de pedidos:
    
    - **date_from**: Fecha desde (opcional, por defecto últimos 30 días)
    - **date_to**: Fecha hasta (opcional, por defecto hoy)
    
    Solo ADMIN_STAFF puede acceder a estas estadísticas.
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

@router.get(
    "/status/{status}",
    response_model=OrderList,
    summary="Obtener pedidos por estado",
    description="Obtener todos los pedidos filtrados por estado específico"
)
async def get_orders_by_status(
    status: OrderStatus,
    skip: int = Query(0, ge=0, description="Número de pedidos a saltar"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de pedidos a retornar"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener pedidos por estado:
    
    - **status**: Estado del pedido
    - **skip**: Número de pedidos a saltar (paginación)
    - **limit**: Número máximo de pedidos a retornar
    
    Los clientes solo ven sus propios pedidos.
    Los ADMIN_STAFF ven todos los pedidos.
    """
    try:
        # Construir filtros
        filters = {"status": status}
        
        # Los clientes solo pueden ver sus propios pedidos
        if current_user.role == "CLIENT":
            filters["user_id"] = current_user.id
        
        # Obtener pedidos
        orders = await Order.find(filters).skip(skip).limit(limit).sort(-Order.created_at).to_list()
        
        # Contar total
        total = await Order.find(filters).count()
        
        # Convertir a respuesta
        order_responses = []
        for order in orders:
            items_response = [
                OrderItemResponse(
                    menu_item_id=str(item.menu_item_id),
                    menu_item_name=item.menu_item_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                    special_instructions=item.special_instructions
                ) for item in order.items
            ]
            
            order_responses.append(OrderResponse(
                id=str(order.id),
                user_id=str(order.user_id),
                items=items_response,
                total=order.total,
                status=order.status,
                notes=order.notes,
                created_at=order.created_at,
                updated_at=order.updated_at
            ))
        
        return OrderList(
            orders=order_responses,
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener pedidos por estado: {str(e)}"
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
    Crear pedido desde el carrito:
    
    - **notes**: Notas adicionales del pedido (opcional)
    
    Convierte todos los items del carrito del usuario en un pedido.
    El carrito se vacía después de crear el pedido exitosamente.
    """
    try:
        # Obtener items del carrito
        from app.models.cart_item import CartItem
        cart_items = await CartItem.find({"user_id": current_user.id}).to_list()
        
        if not cart_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El carrito está vacío"
            )
        
        # Validar y convertir items del carrito a items del pedido
        order_items = []
        total = Decimal('0.00')
        
        for cart_item in cart_items:
            # Obtener item del menú para precio actual
            menu_item = await MenuItem.get(cart_item.menu_item_id)
            if not menu_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item del menú no encontrado: {cart_item.menu_item_name}"
                )
            
            # Verificar disponibilidad
            if not menu_item.available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El item '{menu_item.name}' ya no está disponible"
                )
            
            # Calcular subtotal con precio actual
            subtotal = menu_item.price * cart_item.quantity
            total += subtotal
            
            # Crear OrderItem
            order_item = OrderItem(
                menu_item_id=menu_item.id,
                menu_item_name=menu_item.name,
                quantity=cart_item.quantity,
                unit_price=menu_item.price,
                subtotal=subtotal,
                special_instructions=None  # Los cart_items no tienen instrucciones especiales
            )
            order_items.append(order_item)
        
        # Crear pedido
        order = Order(
            user_id=current_user.id,
            items=order_items,
            total=total,
            notes=notes
        )
        
        # Guardar en la base de datos
        await order.save()
        
        # Limpiar carrito
        await CartItem.find({"user_id": current_user.id}).delete()
        
        # Convertir respuesta
        items_response = [
            OrderItemResponse(
                menu_item_id=str(item.menu_item_id),
                menu_item_name=item.menu_item_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                special_instructions=item.special_instructions
            ) for item in order.items
        ]
        
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