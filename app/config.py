from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb+srv://angelhernades26:<12345>@cluster0.882rxjk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name: str = "restaurant_db"
    
    # Security
    secret_key: str = "your-super-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # App settings
    app_name: str = "Restaurant API"
    app_version: str = "1.0.0"
    debug: bool = True
    
 
    
    # File upload
    upload_folder: str = "uploads"
    max_file_size: int = 10485760  # 10MB
    
    # Android specific
    android_api_version: str = "v1"
    enable_file_upload: bool = True
    compress_images: bool = True
    image_quality: int = 85
    
    class Config:
        env_file = ".env"
        case_sensitive = False

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