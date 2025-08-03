from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from contextlib import asynccontextmanager

from app.database import init_db
from app.core.exceptions import CustomHTTPException
from app.routers import auth, categories, orders, cart
from app.config import settings

from app.routers import main_router


# Lifecycle events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Restaurant API",
    description="API para aplicación de restaurante con gestión de menú y pedidos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# CORS configuration for Android
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Static files for uploaded images if we use filesystem
if not settings.use_azure_storage:
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    
# Custom exception handler
@app.exception_handler(CustomHTTPException)
async def custom_exception_handler(request: Request, exc: CustomHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "error_code": exc.error_code,
            "timestamp": exc.timestamp.isoformat()
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    storage_info = {
        "storage_mode": settings.storage_mode,
        "use_azure_storage": settings.use_azure_storage,
    }
    
    if settings.use_azure_storage:
        storage_info["azure_account"] = settings.azure_storage_account_name
        storage_info["azure_container"] = settings.azure_container_name
        
    return {
        "status": "healthy",
        "service": "Restaurant API",
        "version": "1.0.0",
        "storage": storage_info
    }
    
    
    
# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Restaurant API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
    
    
app.include_router(auth.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
#app.include_router(menu_items.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
#app.include_router(azure_images_router, prefix="/api/v1")
app.include_router(main_router)