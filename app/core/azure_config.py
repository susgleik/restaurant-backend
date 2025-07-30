import os 
from typing import Optional

class AzureConfig:
    # Configuracion de Azure Storage - se lee del OS
    AZURE_STORAGE_ACCOUNT_NAME: str = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
    AZURE_STORAGE_ACCOUNT_KEY: str = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "")
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    
    # Contenedor para imágenes
    CONTAINER_NAME: str = os.getenv("AZURE_CONTAINER_NAME", "restaurant-images")
    
    # CDN (opcional, pero recomendado para producción)
    AZURE_CDN_URL: Optional[str] = os.getenv("AZURE_CDN_URL", None)
    
    # Configuracion de imagenes
    MAX_FILE_SIZE: 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    ALLOWED_MINE_TYPES = {
        "image/jpeg", 
        "image/jpg", 
        "image/png", 
        "image/webp"
    }
    
    # Dimensiones de las imagenes
    MAX_WIDTH = 1200
    MAX_HEIGHT = 800
    QUALITY = 85
    
    @classmethod
    def get_blog_url(cls, blob_name: str) -> str:
        """Genera la URL para acceder a el blob en azure """
        if cls.AZURE_CDN_URL:
            return f"{cls.AZURE_CDN_URL}/{cls.CONTAINER_NAME}/{blob_name}"
        else:
            # se usa la URL directa de blob storage
            return f"https://{cls.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{cls.CONTAINER_NAME}/{blob_name}"
        
    @classmethod
    def validate_config(cls) -> bool:
        """validar que la configuracion de Azure este completa"""
        return bool(
            cls.AZURE_STORAGE_ACCOUNT_NAME and 
            (cls.AZURE_STORAGE_ACCOUNT_KEY or cls.AZURE_STORAGE_CONNECTION_STRING)
        )
        

