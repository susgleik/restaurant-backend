from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.models.user import User
from app.schemas.user_schemas import UserRegister, UserLogin
from fastapi import HTTPException, status
from beanie import PydanticObjectId

# Configuración de encriptación de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verificar contraseña"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generar hash de contraseña"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Crear token JWT"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt
    
    @staticmethod
    def decode_access_token(token: str) -> Optional[str]:
        """Decodificar token JWT y obtener el user_id"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except JWTError:
            return None
    
    @staticmethod
    async def register_user(user_data: UserRegister) -> User:
        """Registrar nuevo usuario"""
        # Verificar si el email ya existe
        existing_user = await User.find_one(User.email == user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # Verificar si el username ya existe
        existing_username = await User.find_one(User.username == user_data.username.lower())
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso"
            )
        
        # Crear hash de la contraseña
        hashed_password = AuthService.get_password_hash(user_data.password)
        
        # Crear usuario
        user = User(
            username=user_data.username.lower(),
            email=user_data.email,
            password=hashed_password,
            role=user_data.role,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Guardar en la base de datos
        await user.insert()
        return user
    
    @staticmethod
    async def authenticate_user(user_data: UserLogin) -> User:
        """Autenticar usuario"""
        # Buscar usuario por email
        user = await User.find_one(User.email == user_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos"
            )
        
        # Verificar contraseña
        if not AuthService.verify_password(user_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email o contraseña incorrectos"
            )
        
        return user
    
    @staticmethod
    async def get_current_user(token: str) -> User:
        """Obtener usuario actual basado en el token"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudieron validar las credenciales",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        user_id = AuthService.decode_access_token(token)
        if user_id is None:
            raise credentials_exception
        
        try:
            user = await User.get(PydanticObjectId(user_id))
            if user is None:
                raise credentials_exception
            return user
        except Exception:
            raise credentials_exception
    
    @staticmethod
    async def change_password(user: User, current_password: str, new_password: str) -> bool:
        """Cambiar contraseña del usuario"""
        # Verificar contraseña actual
        if not AuthService.verify_password(current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual es incorrecta"
            )
        
        # Generar hash de la nueva contraseña
        new_hashed_password = AuthService.get_password_hash(new_password)
        
        # Actualizar contraseña
        user.password = new_hashed_password
        user.updated_at = datetime.utcnow()
        await user.save()
        
        return True