from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.user_schemas import (
    UserRegister, 
    UserLogin, 
    UserResponse, 
    LoginResponse, 
    PasswordChange
)
from app.services.auth_service import AuthService
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Crear una nueva cuenta de usuario en el sistema"
)
async def register(user_data: UserRegister):
    """
    Registrar un nuevo usuario:
    
    - **username**: Nombre de usuario único (3-50 caracteres)
    - **email**: Email válido y único
    - **password**: Contraseña (mínimo 6 caracteres)
    - **role**: Rol del usuario (CLIENT por defecto, ADMIN_STAFF para administradores)
    
    Returns:
    - Información del usuario creado (sin contraseña)
    """
    try:
        user = await AuthService.register_user(user_data)
        
        # Convertir a respuesta sin contraseña
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Iniciar sesión",
    description="Autenticar usuario y obtener token de acceso"
)
async def login(user_data: UserLogin):
    """
    Iniciar sesión:
    
    - **email**: Email del usuario registrado
    - **password**: Contraseña del usuario
    
    Returns:
    - Token de acceso JWT
    - Información del usuario
    """
    try:
        # Autenticar usuario
        user = await AuthService.authenticate_user(user_data)
        
        # Crear token de acceso
        access_token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        
        # Preparar respuesta
        user_response = UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
        return LoginResponse(
            user=user_response,
            access_token=access_token,
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener perfil del usuario actual",
    description="Obtener información del usuario autenticado"
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener perfil del usuario actual:
    
    Requiere autenticación con Bearer Token.
    
    Returns:
    - Información completa del usuario actual
    """
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@router.post(
    "/change-password",
    summary="Cambiar contraseña",
    description="Cambiar la contraseña del usuario actual"
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user)
):
    """
    Cambiar contraseña:
    
    - **current_password**: Contraseña actual
    - **new_password**: Nueva contraseña (mínimo 6 caracteres)
    
    Requiere autenticación con Bearer Token.
    """
    try:
        await AuthService.change_password(
            user=current_user,
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )
        
        return {"message": "Contraseña cambiada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="Refrescar token",
    description="Obtener un nuevo token de acceso"
)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Refrescar token de acceso:
    
    Requiere autenticación con Bearer Token válido.
    
    Returns:
    - Nuevo token de acceso JWT
    - Información actualizada del usuario
    """
    try:
        # Crear nuevo token de acceso
        access_token = AuthService.create_access_token(
            data={"sub": str(current_user.id), "email": current_user.email, "role": current_user.role}
        )
        
        # Preparar respuesta
        user_response = UserResponse(
            id=str(current_user.id),
            username=current_user.username,
            email=current_user.email,
            role=current_user.role,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )
        
        return LoginResponse(
            user=user_response,
            access_token=access_token,
            token_type="bearer"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )