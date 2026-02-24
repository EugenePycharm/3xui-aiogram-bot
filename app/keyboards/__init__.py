"""
Пакет клавиатур для VPN бота.
"""
from app.keyboards.reply import main_menu, get_main_menu
from app.keyboards.inline import (
    get_plans_keyboard,
    get_profile_keyboard,
    get_subscription_keyboard,
    get_referral_keyboard,
)

# Для обратной совместимости
inline_plans = get_plans_keyboard
profile_keyboard = get_profile_keyboard

__all__ = [
    # Reply клавиатуры
    "main_menu",
    "get_main_menu",
    # Inline клавиатуры
    "get_plans_keyboard",
    "get_profile_keyboard",
    "get_subscription_keyboard",
    "get_referral_keyboard",
    # Алиасы для обратной совместимости
    "inline_plans",
    "profile_keyboard",
]
