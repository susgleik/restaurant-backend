from pydantic_settings import BaseSettings
from typing import List
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Permite que las variables del .env sobrescriban los valores por defecto

# Create settings instance
settings = Settings()

# Create upload directories
upload_dirs = [
    settings.upload_folder,
    f"{settings.upload_folder}/images",
    f"{settings.upload_folder}/temp"
]

for directory in upload_dirs:
    if not os.path.exists(directory):
        os.makedirs(directory)