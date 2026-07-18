from aiogram import Router
from .start import router as start_router
from .download import router as download_router

router = Router(name="main_handlers")
router.include_routers(start_router, download_router)
