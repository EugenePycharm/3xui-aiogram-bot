"""
Пакет middleware для VPN бота.
"""
from app.middlewares.clean_messages import CleanMessageMiddleware
from app.middlewares.admin_auth import AdminAuthMiddleware

__all__ = [
    "CleanMessageMiddleware",
    "AdminAuthMiddleware",
]
