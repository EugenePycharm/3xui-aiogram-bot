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
