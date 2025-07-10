from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional
from beanie import PydanticObjectId
from datetime import datetime

from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryList,
)

from app.models.category import Category
from app.models.user import User
from app.core.deps import get_current_admin_user

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get(
    "/",
    response_model=CategoryList,
    summary="Obtener lista de categorias",
    description="Obtiene una lista de todas las categorías disponibles.",
) 
async def get_categories(
    active_only: Optional[bool] = Query(None,description="Filtrar categorías activas (True) o inactivas (False). Si no se especifica, se devuelven todas las categorías.",
    ),
    skip: int = Query(0, ge=0, description="Número de categorías a saltar"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de categorías a retornar")
):
    """
     Obtener lista de categorías:
    
    - **active_only**: Si es True, solo retorna categorías activas
    - **skip**: Número de categorías a saltar (paginación)
    - **limit**: Número máximo de categorías a retornar
    
    No requiere autenticación.
    """
    try:
        # Construir filtro
        filters = {}
        if active_only is not None:
            filters["active"] = active_only
            
        # Obtener categorías con paginación
        categories = await Category.find(filters).skip(skip).limit(limit).to_list()
        
        # Contar total
        total = await Category.find(filters).count()
        
        Category_response = [
            CategoryResponse(
                id=str(category.id),
                name=category.name,
                description=category.description,
                active=category.active,
                created_at=category.created_at
            ) for category in categories
        ]
        
        return CategoryList(categories=Category_response, 
                            total=total)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener categorías: {str(e)}"
        )

@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Obtener categoría por ID",
    description="Obtener información de una categoría específica"
)
async def get_category(category_id: str):
    """
    Obtener categoría por ID:
    
    - **category_id**: ID único de la categoría
    
    No requiere autenticación.
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(category_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de categoría inválido"
            )
        
        # Buscar categoría
        category = await Category.get(PydanticObjectId(category_id))
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada"
            )
        
        return CategoryResponse(
            id=str(category.id),
            name=category.name,
            description=category.description,
            active=category.active,
            created_at=category.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener categoría: {str(e)}"
        )

@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva categoría",
    description="Crea una nueva categoría en el sistema."
)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Crear nueva categoría:
    
    - **category_data**: Datos de la nueva categoría
    
    Requiere autenticación como ADMIN_STAFF.
    """
    try:
        # Verificar si la categoría ya existe
        existing_category = await Category.find_one({"name": category_data.name})
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una categoría con ese nombre"
            )   
        
        #crear nueva categoria
        new_category = Category(
            name=category_data.name,
            description=category_data.description,
            active=category_data.active
        )
        
        await new_category.save()
        
        return CategoryResponse(
            id=str(new_category.id),
            name=new_category.name,
            description=new_category.description,
            active=new_category.active,
            created_at=new_category.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear categoría: {str(e)}"
        )

@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Actualizar categoría",
    description="Actualizar una categoría existente (solo ADMIN_STAFF)"
)
async def update_category(
    category_id: str,
    category_data: CategoryUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar categoría:
    
    - **category_id**: ID único de la categoría
    - **name**: Nuevo nombre (opcional)
    - **description**: Nueva descripción (opcional)
    - **active**: Nuevo estado activo (opcional)
    
    Requiere autenticación con rol ADMIN_STAFF.
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(category_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de categoría inválido"
            )
        
        # Buscar categoría
        category = await Category.get(PydanticObjectId(category_id))
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada"
            )
        
        # Verificar si el nuevo nombre ya existe (si se proporciona)
        if category_data.name and category_data.name != category.name:
            existing_category = await Category.find_one({"name": category_data.name})
            if existing_category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe una categoría con este nombre"
                )
        
        # Actualizar campos
        update_data = category_data.dict(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                setattr(category, field, value)
            
            # Guardar cambios
            await category.save()
        
        return CategoryResponse(
            id=str(category.id),
            name=category.name,
            description=category.description,
            active=category.active,
            created_at=category.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar categoría: {str(e)}"
        )

@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar categoría",
    description="Eliminar una categoría existente (solo ADMIN_STAFF)"
)
async def delete_category(
    category_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar categoría:
    
    - **category_id**: ID único de la categoría
    
    Requiere autenticación con rol ADMIN_STAFF.
    
    Nota: No se puede eliminar una categoría que tenga items del menú asociados.
    """
    try:
        # Validar ObjectId
        if not PydanticObjectId.is_valid(category_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de categoría inválido"
            )
        
        # Buscar categoría
        category = await Category.get(PydanticObjectId(category_id))
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categoría no encontrada"
            )
        
        # Verificar si tiene items asociados
        from app.models.menu_item import MenuItem
        items_count = await MenuItem.find({"category_id": category.id}).count()
        if items_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se puede eliminar la categoría porque tiene {items_count} items del menú asociados"
            )
        
        # Eliminar categoría
        await category.delete()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar categoría: {str(e)}"
        )