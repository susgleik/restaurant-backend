from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import AuthService
from app.models.user import User, UserRole
from typing import Optional

# Esquema de autenticación Bearer
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Dependencia para obtener el usuario actual"""
    token = credentials.credentials
    user = await AuthService.get_current_user(token)
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependencia para obtener usuario activo"""
    # Aquí podrías agregar validaciones adicionales como:
    # - Usuario bloqueado
    # - Usuario verificado
    # - etc.
    return current_user

async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Dependencia para obtener usuario administrador"""
    if current_user.role != UserRole.ADMIN_STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción"
        )
    return current_user

def get_optional_user():
    """Dependencia opcional para obtener usuario (puede ser None)"""
    async def _get_optional_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(
            HTTPBearer(auto_error=False)
        )
    ) -> Optional[User]:
        if credentials is None:
            return None
        
        try:
            token = credentials.credentials
            user = await AuthService.get_current_user(token)
            return user
        except HTTPException:
            return None
    
    return _get_optional_user