"""
Хендлеры для профиля пользователя.
"""
from datetime import datetime

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from app.database import requests as rq
from app.keyboards import get_referral_keyboard
from app.utils import MessageCleaner, extract_base_host, get_subscription_link

router = Router()


@router.message(F.text == '👤 Профиль')
async def profile(message: Message) -> None:
    """
    Показ профиля пользователя.
    
    Args:
        message: Сообщение от пользователя
    """
    user = await rq.select_user(message.from_user.id)
    sub = await rq.get_user_subscription(user.tg_id)
    referrals_count = await rq.get_referrals_count(user.id)

    text = _build_profile_text(user, sub, referrals_count)
    markup = _build_profile_markup(sub)

    # Очищаем старые сообщения профиля
    await MessageCleaner.clear_old_messages(message.from_user.id, max_messages=1)

    await message.answer(text, reply_markup=markup, parse_mode="Markdown")


def _build_profile_text(
    user,
    sub,
    referrals_count: int
) -> str:
    """
    Построение текста профиля.
    
    Args:
        user: Объект пользователя
        sub: Объект подписки или None
        referrals_count: Количество рефералов
    
    Returns:
        Текст профиля
    """
    text = "👤 **Профиль**\n\n"
    text += f"🆔 ID: `{user.tg_id}`\n"
    text += f"💰 Баланс: {user.balance} RUB\n"
    text += f"👥 Приглашено друзей: {referrals_count}\n\n"

    if sub:
        expiry = sub.expires_at.strftime("%d.%m.%Y")
        days_left = (sub.expires_at - datetime.now()).days

        text += "🔑 **Активная подписка**\n"
        text += f"📅 Истекает: {expiry} ({days_left} дн.)\n"
        text += f"🌍 Сервер: {sub.server.location}\n"
    else:
        text += "❌ Нет активной подписки."

    return text


def _build_profile_markup(sub) -> InlineKeyboardMarkup:
    """
    Построение клавиатуры профиля.
    
    Args:
        sub: Объект подписки или None
    
    Returns:
        InlineKeyboardMarkup
    """
    if sub:
        builder = InlineKeyboardBuilder()
        
        base_host = extract_base_host(sub.server.api_url)
        sub_link = get_subscription_link(base_host, sub.email)
        
        builder.row(
            InlineKeyboardButton(text="📥 Моя подписка", url=sub_link)
        )
        builder.row(
            InlineKeyboardButton(text="🔑 Посмотреть мой ключ", callback_data="view_key")
        )
        builder.row(
            InlineKeyboardButton(text="👥 Пригласить друга", callback_data="ref_link")
        )
        return builder.as_markup()
    else:
        return get_referral_keyboard().as_markup()


@router.callback_query(F.data == "view_key")
async def view_key(callback: CallbackQuery) -> None:
    """
    Показ ключа подписки.
    
    Args:
        callback: Callback query от пользователя
    """
    sub = await rq.get_user_subscription(callback.from_user.id)
    
    if sub:
        msg = (
            f"🔑 **Ваш ключ:**\n"
            f"`{sub.key_url}`\n\n"
            f"👆 Нажмите на текст ключа, чтобы скопировать его."
        )
        await callback.message.answer(msg, parse_mode="Markdown")
        await callback.answer()
    else:
        await callback.answer("Подписка не найдена.", show_alert=True)
