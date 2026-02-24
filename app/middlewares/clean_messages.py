"""
Middleware для автоматической очистки сообщений.
Предотвращает захламление чата старыми сообщениями.
"""
import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.utils.messages import MessageCleaner

logger = logging.getLogger(__name__)


class CleanMessageMiddleware(BaseMiddleware):
    """
    Middleware для автоматической очистки старых сообщений.
    
    Принцип работы:
    - При каждом сообщении от пользователя очищаем его старые сообщения от бота
    - Оставляем только последние N сообщений для каждого пользователя
    """

    def __init__(self, max_messages: int = 3):
        """
        Инициализация middleware.
        
        Args:
            max_messages: Максимальное количество сообщений для хранения
        """
        self.max_messages = max_messages

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[None]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события.
        
        Args:
            handler: Следующий обработчик в цепочке
            event: Событие (сообщение или callback)
            data: Данные контекста
        
        Returns:
            Результат выполнения обработчика
        """
        # Получаем ID пользователя
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)

        # Автоматически очищаем старые сообщения
        await MessageCleaner.clear_old_messages(user_id, max_messages=self.max_messages)

        return await handler(event, data)
