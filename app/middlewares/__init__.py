"""
Пакет middleware для VPN бота.
"""
from app.middlewares.clean_messages import CleanMessageMiddleware

__all__ = [
    "CleanMessageMiddleware",
]
