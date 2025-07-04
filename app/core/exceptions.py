from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class CustomHTTPException(HTTPException):
    """
    Excepción HTTP personalizada con información adicional para Android
    """
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        headers: Optional[Dict[str, Any]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or f"ERROR_{status_code}"
        self.timestamp = datetime.utcnow()
        self.extra_data = extra_data or {}

# Excepciones de autenticación
class AuthenticationException(CustomHTTPException):
    """Excepciones relacionadas con autenticación"""
    def __init__(self, detail: str = "Authentication failed", error_code: str = "AUTH_FAILED"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code,
            headers={"WWW-Authenticate": "Bearer"}
        )

class InvalidCredentialsException(AuthenticationException):
    """Credenciales inválidas"""
    def __init__(self):
        super().__init__(
            detail="Invalid username or password",
            error_code="INVALID_CREDENTIALS"
        )

class TokenExpiredException(AuthenticationException):
    """Token expirado"""
    def __init__(self):
        super().__init__(
            detail="Token has expired",
            error_code="TOKEN_EXPIRED"
        )

class InvalidTokenException(AuthenticationException):
    """Token inválido"""
    def __init__(self):
        super().__init__(
            detail="Invalid token",
            error_code="INVALID_TOKEN"
        )

# Excepciones de autorización
class AuthorizationException(CustomHTTPException):
    """Excepciones relacionadas con autorización"""
    def __init__(self, detail: str = "Not enough permissions", error_code: str = "INSUFFICIENT_PERMISSIONS"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code
        )

class AdminRequiredException(AuthorizationException):
    """Se requieren permisos de administrador"""
    def __init__(self):
        super().__init__(
            detail="Administrator permissions required",
            error_code="ADMIN_REQUIRED"
        )

class StaffRequiredException(AuthorizationException):
    """Se requieren permisos de staff"""
    def __init__(self):
        super().__init__(
            detail="Staff permissions required",
            error_code="STAFF_REQUIRED"
        )

# Excepciones de validación
class ValidationException(CustomHTTPException):
    """Excepciones de validación de datos"""
    def __init__(self, detail: str, field: str = None, error_code: str = "VALIDATION_ERROR"):
        extra_data = {"field": field} if field else {}
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code=error_code,
            extra_data=extra_data
        )

class DuplicateValueException(ValidationException):
    """Valor duplicado"""
    def __init__(self, field: str, value: str):
        super().__init__(
            detail=f"{field} '{value}' already exists",
            field=field,
            error_code="DUPLICATE_VALUE"
        )

class InvalidFormatException(ValidationException):
    """Formato inválido"""
    def __init__(self, field: str, expected_format: str):
        super().__init__(
            detail=f"Invalid format for {field}. Expected: {expected_format}",
            field=field,
            error_code="INVALID_FORMAT"
        )

# Excepciones de recursos
class ResourceNotFoundException(CustomHTTPException):
    """Recurso no encontrado"""
    def __init__(self, resource: str, identifier: str = None):
        detail = f"{resource} not found"
        if identifier:
            detail += f" with id: {identifier}"
        
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="RESOURCE_NOT_FOUND",
            extra_data={"resource": resource, "identifier": identifier}
        )

class ResourceAlreadyExistsException(CustomHTTPException):
    """Recurso ya existe"""
    def __init__(self, resource: str, identifier: str = None):
        detail = f"{resource} already exists"
        if identifier:
            detail += f" with id: {identifier}"
        
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="RESOURCE_ALREADY_EXISTS",
            extra_data={"resource": resource, "identifier": identifier}
        )

class ResourceConflictException(CustomHTTPException):
    """Conflicto con el estado del recurso"""
    def __init__(self, detail: str, resource: str = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="RESOURCE_CONFLICT",
            extra_data={"resource": resource}
        )

# Excepciones de negocio específicas del restaurante
class MenuItemNotAvailableException(CustomHTTPException):
    """Item del menú no disponible"""
    def __init__(self, item_name: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Menu item '{item_name}' is not available",
            error_code="MENU_ITEM_NOT_AVAILABLE",
            extra_data={"item_name": item_name}
        )

class InsufficientStockException(CustomHTTPException):
    """Stock insuficiente"""
    def __init__(self, item_name: str, requested: int, available: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock for '{item_name}'. Requested: {requested}, Available: {available}",
            error_code="INSUFFICIENT_STOCK",
            extra_data={
                "item_name": item_name,
                "requested": requested,
                "available": available
            }
        )

class OrderNotFoundException(ResourceNotFoundException):
    """Pedido no encontrado"""
    def __init__(self, order_id: str):
        super().__init__("Order", order_id)

class InvalidOrderStatusException(CustomHTTPException):
    """Estado de pedido inválido"""
    def __init__(self, current_status: str, requested_status: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot change order status from '{current_status}' to '{requested_status}'",
            error_code="INVALID_ORDER_STATUS_TRANSITION",
            extra_data={
                "current_status": current_status,
                "requested_status": requested_status
            }
        )

class EmptyCartException(CustomHTTPException):
    """Carrito vacío"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create order from empty cart",
            error_code="EMPTY_CART"
        )

# Excepciones de archivos
class FileUploadException(CustomHTTPException):
    """Error en subida de archivos"""
    def __init__(self, detail: str, error_code: str = "FILE_UPLOAD_ERROR"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code
        )

class FileTooLargeException(FileUploadException):
    """Archivo demasiado grande"""
    def __init__(self, max_size: int):
        super().__init__(
            detail=f"File size exceeds maximum allowed size of {max_size} bytes",
            error_code="FILE_TOO_LARGE"
        )

class InvalidFileTypeException(FileUploadException):
    """Tipo de archivo inválido"""
    def __init__(self, allowed_types: list):
        super().__init__(
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
            error_code="INVALID_FILE_TYPE"
        )

# Excepciones de base de datos
class DatabaseException(CustomHTTPException):
    """Error de base de datos"""
    def __init__(self, detail: str = "Database error occurred"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="DATABASE_ERROR"
        )

class DatabaseConnectionException(DatabaseException):
    """Error de conexión a base de datos"""
    def __init__(self):
        super().__init__(
            detail="Unable to connect to database"
        )