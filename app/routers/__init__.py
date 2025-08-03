"""
principal module for routers
this module imports all the routers and initializes them
"""
from fastapi import APIRouter

from .menu_items import router as menu_items_router

main_router = APIRouter(prefix="/api/v1")

main_router.include_router(
    menu_items_router,
    prefix="/menu-items",
    tags=["Menu Items"]
)

__all__ = [
    "menu_items_router",
]

#metada for the module 
__version__ = "1.0.0"
__description__ = "Main router for the application, includes all sub-routers."