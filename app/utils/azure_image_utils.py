import uuid
import asyncio
from io import BytesIO
from pathlib import Path
from PIL import Image
from fastapi import HTTPException, UploadFile
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import ContentSettings
from azure.core.exceptions import AzureError
from typing import Optional, List
from app.config import settings

class AzureImageProcessor:
    
    def __init__(self):
        if not settings.use_azure_storage:
            raise ValueError("Azure blob Storage is not configured.")
        
        # Crear cliente de azure blob storage usando config ???
        if settings.azure_storage_connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
        else:
            account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=settings.azure_storage_account_key
            )
    
    async def ensure_container_exists(self):
        """ create container if not exists """
        try:
            container_client = self.blob_service_client.get_container_client(
                settings.azure_container_name
            )
            
            if not await container_client.exists():
                await container_client.create_container(
                    public_access="blob"
                )
                print(f"Container '{settings.azure_container_name}' created.")
            else:
                print(f"Container '{settings.azure_container_name}' already exists.")
        
        except AzureError as e:
            print(f"Error ensuring container exists: {e}")
            raise HTTPException(
                status_code=500, 
                detail="Error ensuring container exists.")
            
    @staticmethod
    def validate_file(file: UploadFile) -> None:
        """validate file using main config"""
        # using config.py config
        allowed_extensions = {f".{ext}" for ext in settings.allowed_file_extensions.split(",")}
        allowed_mime_types = {
            "image/jpeg", 
            "image/jpg", 
            "image/png", 
            "image/webp",
            "image/gif"
        }
        
        # check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file extension: {file_extension}. Allowed extensions: {', '.join(allowed_extensions)}"
            )
        
        # check mime type
        if file.content_type not in allowed_mime_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid MIME type: {file.content_type}. Allowed types: {', '.join(allowed_mime_types)}"
            )
        
        @staticmethod
        def generate_blob_name(original_filename: str, folder: str = "menu-items") -> str:
            """Generate a unique blob name based on the original filename."""
            file_extension = Path(original_filename).suffix.lower()
            unique_id = str(uuid.uuid4())
            return f"{folder}/{unique_id}{file_extension}"
        
        @staticmethod
        def process_image_in_memory(image_data: bytes) -> bytes:
            """Procesar y optimizar imagen en memoria usando config principal"""
            try:
                # Abrir imagen desde bytes
                image = Image.open(BytesIO(image_data))
                
                # Convertir a RGB si es necesario
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                
                # Redimensionar si es necesario (usar config de tu settings)
                width, height = image.size
                max_width = 1200  # Valor por defecto, puedes agregarlo a tu config
                max_height = 800   # Valor por defecto, puedes agregarlo a tu config
                
                if width > max_width or height > max_height:
                    image.thumbnail(
                        (max_width, max_height),
                        Image.Resampling.LANCZOS
                    )
                
                # Guardar en BytesIO optimizada usando image_quality de tu config
                output = BytesIO()
                image.save(
                    output,
                    format='JPEG',
                    quality=settings.image_quality,  # Usar tu configuración
                    optimize=True
                )
                
                return output.getvalue()
                
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error procesando imagen: {str(e)}"
                )
    
        async def upload_image(self, file: UploadFile, folder: str = "menu-items") -> str:
            """Proceso completo de subida de imagen a Azure Blob Storage"""
            try:
                # Asegurar que existe el contenedor
                await self.ensure_container_exists()
                
                # Validar archivo
                self.validate_file(file)
                
                # Leer contenido del archivo
                file_content = await file.read()
                
                # Verificar tamaño usando tu config
                if len(file_content) > settings.max_file_size:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Archivo muy grande. Máximo permitido: {settings.max_file_size // (1024*1024)}MB"
                    )
                
                # Procesar imagen
                processed_image = self.process_image_in_memory(file_content)
                
                # Generar nombre único para el blob
                blob_name = self.generate_blob_name(file.filename, folder)
                
                # Configurar content settings
                content_settings = ContentSettings(
                    content_type="image/jpeg",
                    cache_control="public, max-age=3600"  # Cache por 1 hora
                )
                
                # Subir a Azure Blob Storage
                blob_client = self.blob_service_client.get_blob_client(
                    container=settings.azure_container_name,
                    blob=blob_name
                )
                
                await blob_client.upload_blob(
                    data=processed_image,
                    content_settings=content_settings,
                    overwrite=True
                )
                
                # Retornar URL usando tu config
                return settings.get_azure_blob_url(blob_name)
                
            except HTTPException:
                raise
            except AzureError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error de Azure Blob Storage: {str(e)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error al subir imagen: {str(e)}"
                )
                
        async def delete_image(self, image_url: str) -> bool:
            """Eliminar imagen de Azure Blob Storage"""
            try:
                # Extract blob name from URL
                if settings.azure_cdn_url and settings.azure_cdn_url in image_url:
                    # URL con CDN
                    blob_name = image_url.split(f"/{settings.azure_container_name}/")[1]
                else:
                    # URL directa de Azure Blob Storage
                    blob_name = image_url.split(f"{settings.azure_container_name}/")[1]
                
                #eliminar blob
                blob_client = self.blob_service_client.get_blob_client(
                    container=settings.azure_container_name,
                    blob=blob_name
                )
                await blob_client.delete_blob()
                print(f"image deleted successfully: {blob_name}")
                return True
            except AzureError as e:
                return False
            except Exception as e:
                return False
            
        async def list_images(self, folder: str = "menu-items") -> List[dict]:
            """ Listar imágenes en un contenedor de Azure Blob Storage """
            try:
                await self.ensure_container_exists()
                container_client = self.blob_service_client.get_container_client(
                    settings.azure_container_name
                )
                
                images = []                
                async for blob in container_client.list_blobs(name_starts_with=folder):
                    images.apppend({
                        "filename": blob.name.split("/")[-1],
                        "blob_name": blob.name,
                        "url": settings.get_azure_blob_url(blob.name),
                        "size": blob.size,
                        "created": blob.creation_time.isoformat() if blob.creation_time else None,
                        "last_modified": blob.last_modified.isoformat() if blob.last_modified else None
                    })
                
                return sorted(images, key=lambda x: x['last_modified'] or "", reverse=True)
            
            except AzureError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error al listar imágenes: {str(e)}"
                )
                
        async def close(self):
            """Cerrar conexión con Azure Blob Storage"""
            await self.blob_service_client.close()
            