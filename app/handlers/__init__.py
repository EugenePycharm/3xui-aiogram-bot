"""
Пакет хендлеров для VPN бота.
Собирает все роутеры в один главный router.
"""
from aiogram import Router

from app.handlers.start import router as start_router
from app.handlers.profile import router as profile_router
from app.handlers.subscription import router as subscription_router
from app.handlers.payment import router as payment_router
from app.handlers.support import router as support_router

# Главный роутер, включающий все обработчики
router = Router()

# Подключаем все роутеры
router.include_router(start_router)
router.include_router(profile_router)
router.include_router(subscription_router)
router.include_router(payment_router)
router.include_router(support_router)

__all__ = ["router"]
