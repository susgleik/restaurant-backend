from fastapi import APIRouter

from .menu_items_gets import router as menu_items_gets_router
from .menu_items_posts import router as menu_items_posts_router
from .menu_items_puts import router as menu_items_puts_router
from .menu_items_patch import router as menu_items_patch_router
from .menu_items_deletes import router as menu_items_deletes_router

# main router for menu items
router = APIRouter()

router.include_router(menu_items_gets_router)
router.include_router(menu_items_posts_router)  
router.include_router(menu_items_puts_router)
router.include_router(menu_items_patch_router)
router.include_router(menu_items_deletes_router)

# Metadata
__version__ = "1.0.0"
__description__ = "Módulo de endpoints para gestión de items del menú"

# Exportar
__all__ = ["router"]