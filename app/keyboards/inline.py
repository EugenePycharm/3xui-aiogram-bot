"""
Inline-клавиатуры для бота.
"""
from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import Plan


async def get_plans_keyboard(plans: List[Plan]) -> InlineKeyboardMarkup:
    """
    Клавиатура с тарифными планами.

    Args:
        plans: Список тарифных планов

    Returns:
        InlineKeyboardMarkup с кнопками тарифов
    """
    keyboard = InlineKeyboardBuilder()

    for plan in plans:
        if plan.price > 0:  # Не показывать trial планы
            keyboard.add(
                InlineKeyboardButton(
                    text=f"{plan.name} - {plan.price} RUB",
                    callback_data=f"buy_plan_{plan.id}"
                )
            )

    return keyboard.adjust(1).as_markup()


async def get_servers_keyboard(servers_with_stats: list) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора сервера с индикаторами заполненности.

    Args:
        servers_with_stats: Список кортежей (Server, sub_count)

    Returns:
        InlineKeyboardMarkup с кнопками серверов
    """
    keyboard = InlineKeyboardBuilder()

    for server, sub_count in servers_with_stats:
        # Вычисляем процент заполненности
        max_clients = server.max_clients or 50  # Default 50 if not set
        fill_percent = (sub_count / max_clients) * 100 if max_clients > 0 else 0

        # Выбираем индикатор
        if fill_percent >= 80:
            indicator = "🔴"  # Красный - почти заполнен
        elif fill_percent >= 50:
            indicator = "🟡"  # Жёлтый - средняя заполненность
        else:
            indicator = "🟢"  # Зелёный - свободно

        # Формируем текст кнопки
        location_flag = _get_location_flag(server.location)
        button_text = f"{location_flag} {server.name}  {indicator}"

        keyboard.add(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"select_server_{server.id}"
            )
        )

    keyboard.adjust(1)
    return keyboard.as_markup()


def _get_location_flag(location: str) -> str:
    """
    Получить флаг страны по названию локации.

    Args:
        location: Название локации

    Returns:
        Эмодзи флага
    """
    flags = {
        "germany": "🇩🇪",
        "german": "🇩🇪",
        "de": "🇩🇪",
        "france": "🇫🇷",
        "french": "🇫🇷",
        "fr": "🇫🇷",
        "netherlands": "🇳🇱",
        "nl": "🇳🇱",
        "usa": "🇺🇸",
        "united states": "🇺🇸",
        "uk": "🇬🇧",
        "united kingdom": "🇬🇧",
        "poland": "🇵🇱",
        "pl": "🇵🇱",
        "spain": "🇪🇸",
        "es": "🇪🇸",
        "italy": "🇮🇹",
        "it": "🇮🇹",
        "turkey": "🇹🇷",
        "tr": "🇹🇷",
        "russia": "🇷🇺",
        "ru": "🇷🇺",
        "kazakhstan": "🇰🇿",
        "kz": "🇰🇿",
        "ukraine": "🇺🇦",
        "ua": "🇺🇦",
    }

    location_lower = location.lower()
    for key, flag in flags.items():
        if key in location_lower:
            return flag

    return "🌍"  # Default flag


async def get_profile_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура профиля.

    Returns:
        InlineKeyboardMarkup с кнопками профиля
    """
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="ref_link")
    )
    return keyboard.adjust(1).as_markup()


def get_subscription_keyboard(sub_link: str) -> InlineKeyboardMarkup:
    """
    Клавиатура с ссылками на подписку.

    Args:
        sub_link: Ссылка на подписку

    Returns:
        InlineKeyboardMarkup с кнопками подписки
    """
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="📥 Моя подписка", url=sub_link)
    )
    keyboard.row(
        InlineKeyboardButton(text="🔑 Посмотреть мой ключ", callback_data="view_key")
    )
    return keyboard.as_markup()


def get_referral_keyboard() -> InlineKeyboardBuilder:
    """
    Клавиатура для профиля с реферальной кнопкой.

    Returns:
        InlineKeyboardBuilder с кнопкой реферала
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Пригласить друга", callback_data="ref_link")
    )
    return builder
