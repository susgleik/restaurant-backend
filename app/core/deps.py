from fastapi import Depends, HTTPException, status
from app.core.security import get_current_active_user
from app.models.user import User, UserRole

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependencia para verificar que el usuario actual es ADMIN_STAFF
    """
    if current_user.role != UserRole.ADMIN_STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción. Se requiere rol ADMIN_STAFF."
        )
    return current_user

async def get_current_client_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependencia para verificar que el usuario actual es CLIENT
    """
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción. Se requiere rol CLIENT."
        )
    return current_user