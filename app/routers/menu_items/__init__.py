from fastapi import APIRouter

from .menu_items_gets import router as menu_items_gets_router
from .menu_items_posts import router as menu_items_posts_router
from .menu_items_puts import router as menu_items_puts_router
from .menu_items_patch import router as menu_items_patch_router
from .menu_items_deletes import router as menu_items_deletes_router

# main router for menu items
router = APIRouter()

router.include_router(menu_items_gets_router, tags=["Menu Items - Read"])
router.include_router(menu_items_posts_router, tags=["Menu Items - Create"])  
router.include_router(menu_items_puts_router, tags=["Menu Items - Update"])
router.include_router(menu_items_patch_router, tags=["Menu Items - Partial Update"])
router.include_router(menu_items_deletes_router, tags=["Menu Items - Delete"])

# Metadata
__version__ = "1.0.0"
__description__ = "Módulo de endpoints para gestión de items del menú"

# Exportar
__all__ = ["router"]