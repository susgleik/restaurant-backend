from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Database
    mongodb_url: str 
    database_name: str = "restaurant_db"
    
    # Security  
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # App settings
    app_name: str = "Restaurant API"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # File upload
    upload_folder: str = "uploads"
    max_file_size: int = 10485760  # 10MB
    allowed_file_extensions: str = "jpg,jpeg,png,gif,webp"

     # SMTP Configuration
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = "your-email@gmail.com"
    smtp_password: str = "your-app-password"
    
    # CORS settings
    allowed_origins: str = "*"
    allowed_methods: str = "GET,POST,PUT,DELETE,OPTIONS"
    allowed_headers: str = "*"
    
    # Android specific
    android_api_version: str = "v1"
    enable_file_upload: bool = True
    compress_images: bool = True
    image_quality: int = 85
    
    # Azure Blob Storage (nuevos campos)
    azure_storage_account_name: str = ""
    azure_storage_account_key: str = ""
    azure_storage_connection_string: str = ""
    azure_container_name: str = "restaurant-images"
    azure_cdn_url: Optional[str] = None
    
    # Storage mode: "filesystem" o "azure"
    storage_mode: str = "azure"  # Por defecto filesystem para compatibilidad
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore" 
        # Permite que las variables del .env sobrescriban los valores por defecto
    
    @property
    def use_azure_storage(self) -> bool:
        """Determina si se está usando Azure Storage"""
        return (
            self.storage_mode.lower() == "azure" and
            self.azure_storage_account_name and 
            (self.azure_storage_account_key or self.azure_storage_connection_string)
        )
    
    def get_azure_blob_url(self, blob_name: str) -> str:
        """Generar URL completa para un blob de Azure"""
        if self.azure_cdn_url:
            return f"{self.azure_cdn_url}/{self.azure_container_name}/{blob_name}"
        else:
            return f"https://{self.azure_storage_account_name}.blob.core.windows.net/{self.azure_container_name}/{blob_name}"

# Create settings instance
settings = Settings()

# Create upload directories solo si usamos filesystem
if not settings.use_azure_storage:
    upload_dirs = [
        settings.upload_folder,
        f"{settings.upload_folder}/images",
        f"{settings.upload_folder}/temp"
    ]

    for directory in upload_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            
# Imprimir modo de almacenamiento para debug
if settings.debug:
    storage_type = "Azure Blob Storage" if settings.use_azure_storage else "Filesystem"
    print(f"🗂️  Modo de almacenamiento: {storage_type}")
    if settings.use_azure_storage:
        print(f"📦 Container Azure: {settings.azure_container_name}")
        print(f"🌐 Account: {settings.azure_storage_account_name}")
    else:
        print(f"📁 Directorio local: {settings.upload_folder}")