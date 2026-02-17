"""
Утилиты для управления сообщениями Telegram.
Безопасное удаление и редактирование сообщений.
"""
import logging
from typing import List, Optional

from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


async def delete_message_safe(message: Message) -> bool:
    """
    Безопасное удаление сообщения.
    
    Args:
        message: Сообщение для удаления
    
    Returns:
        True если успешно, False если ошибка или сообщение уже удалено
    """
    try:
        await message.delete()
        return True
    except TelegramBadRequest as e:
        error_text = str(e).lower()
        if "message to delete not found" in error_text or "message can't be deleted" in error_text:
            logger.debug(f"Сообщение уже удалено или не может быть удалено: {e}")
            return False
        logger.warning(f"Ошибка при удалении сообщения: {e}")
        return False
    except Exception as e:
        logger.warning(f"Неожиданная ошибка при удалении сообщения: {e}")
        return False


async def delete_messages_safe(messages: List[Message]) -> int:
    """
    Безопасное удаление списка сообщений.
    
    Args:
        messages: Список сообщений для удаления
    
    Returns:
        Количество успешно удалённых сообщений
    """
    deleted_count = 0
    for msg in messages:
        if await delete_message_safe(msg):
            deleted_count += 1
    return deleted_count


async def edit_or_delete_safe(
    message: Message,
    new_text: str,
    **kwargs
) -> bool:
    """
    Попытка отредактировать сообщение, а при неудаче - удалить его.
    
    Args:
        message: Сообщение для редактирования
        new_text: Новый текст сообщения
        **kwargs: Дополнительные аргументы для edit_text
    
    Returns:
        True если отредактировано, False если удалено или ошибка
    """
    try:
        await message.edit_text(new_text, **kwargs)
        return True
    except TelegramBadRequest as e:
        error_text = str(e).lower()
        if "message can't be edited" in error_text or "message is not modified" in error_text:
            try:
                await message.delete()
                return False  # Удалено, а не отредактировано
            except Exception:
                return False
        logger.warning(f"Ошибка при редактировании сообщения: {e}")
        return False
    except Exception as e:
        logger.warning(f"Неожиданная ошибка при редактировании: {e}")
        return False


class MessageCleaner:
    """
    Менеджер для отслеживания и очистки сообщений бота.
    Используется для предотвращения накопления сообщений в чате.
    
    Class attributes:
        _storage: Словарь {user_id: [messages]} для хранения сообщений
    """

    _storage: dict[int, list[Message]] = {}

    @classmethod
    def add_message(cls, user_id: int, message: Message) -> None:
        """
        Добавить сообщение в список для последующей очистки.
        
        Args:
            user_id: ID пользователя
            message: Сообщение для отслеживания
        """
        if user_id not in cls._storage:
            cls._storage[user_id] = []
        cls._storage[user_id].append(message)

        # Ограничиваем хранение последними 10 сообщениями
        if len(cls._storage[user_id]) > 10:
            cls._storage[user_id] = cls._storage[user_id][-10:]

    @classmethod
    async def clear_user_messages(cls, user_id: int, keep_last: int = 0) -> int:
        """
        Удалить все tracked сообщения пользователя.
        
        Args:
            user_id: ID пользователя
            keep_last: Сколько последних сообщений сохранить
        
        Returns:
            Количество удалённых сообщений
        """
        if user_id not in cls._storage:
            return 0

        messages_to_delete = (
            cls._storage[user_id][:-keep_last]
            if keep_last > 0
            else cls._storage[user_id]
        )
        cls._storage[user_id] = (
            cls._storage[user_id][-keep_last:]
            if keep_last > 0
            else []
        )

        deleted_count = 0
        for msg in messages_to_delete:
            if await delete_message_safe(msg):
                deleted_count += 1

        return deleted_count

    @classmethod
    async def clear_old_messages(cls, user_id: int, max_messages: int = 3) -> int:
        """
        Удалить старые сообщения, оставив только последние max_messages.
        
        Args:
            user_id: ID пользователя
            max_messages: Максимальное количество сообщений для хранения
        
        Returns:
            Количество удалённых сообщений
        """
        if user_id not in cls._storage or len(cls._storage[user_id]) <= max_messages:
            return 0

        messages_to_delete = cls._storage[user_id][:-max_messages]
        cls._storage[user_id] = cls._storage[user_id][-max_messages:]

        deleted_count = 0
        for msg in messages_to_delete:
            if await delete_message_safe(msg):
                deleted_count += 1

        return deleted_count

    @classmethod
    def get_last_message(cls, user_id: int) -> Optional[Message]:
        """
        Получить последнее сохранённое сообщение пользователя.
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Последнее сообщение или None
        """
        if user_id in cls._storage and cls._storage[user_id]:
            return cls._storage[user_id][-1]
        return None

    @classmethod
    def clear_all(cls) -> None:
        """Очистить всё хранилище сообщений (для тестов или сброса)."""
        cls._storage.clear()
