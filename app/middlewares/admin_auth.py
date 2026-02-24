"""
Middleware для проверки прав администратора.
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.database.models import Admin
from app.database import requests as rq

logger = logging.getLogger(__name__)


class AdminAuthMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора."""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем tg_id из сообщения или callback query
        if isinstance(event, Message):
            tg_id = event.from_user.id
            username = event.from_user.username
            logger.debug(f"Middleware: Message from user {tg_id} (@{username})")
        elif isinstance(event, CallbackQuery):
            tg_id = event.from_user.id
            username = event.from_user.username
            logger.debug(f"Middleware: CallbackQuery from user {tg_id} (@{username})")
        else:
            return await handler(event, data)

        # Проверяем, является ли пользователь администратором
        admin = await rq.get_admin_by_tg_id(tg_id)
        logger.debug(f"Middleware: Admin lookup for {tg_id} returned {admin}")

        if not admin or not admin.is_active:
            logger.warning(f"Попытка доступа к админ-панели от пользователя {tg_id} (@{username})")
            if isinstance(event, Message):
                try:
                    await event.answer("⛔ Доступ запрещён. Вы не являетесь администратором.")
                except Exception as e:
                    logger.error(f"Error sending answer: {e}")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещён. Вы не являетесь администратором.", show_alert=True)
            return None

        # Добавляем администратора в контекст
        data["admin"] = admin
        data["admin_tg_id"] = tg_id

        logger.debug(f"Admin {tg_id} authenticated successfully")
        return await handler(event, data)
