"""
Роутер для админ-бота.
Собирает все роутеры админ-панели.
"""
import logging
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.database import requests as rq
from app.database.models import Admin
from app.keyboards.admin import get_admin_main_keyboard

from app.handlers.admin import subscriptions, users, servers

logger = logging.getLogger(__name__)

# Главный роутер админ-бота
router = Router()

# Подключаем все роутеры
router.include_router(subscriptions.router)
router.include_router(users.router)
router.include_router(servers.router)


@router.message(Command("start"))
async def admin_start_command(message: Message, admin: Admin) -> None:
    """Команда /start для админ-бота."""
    await message.answer(
        f"👋 <b>Панель администратора</b>\n\n"
        f"Админ: {admin.username or admin.tg_id}\n\n"
        f"Выберите раздел:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("admin"))
async def admin_panel_command(message: Message, admin: Admin) -> None:
    """Команда /admin для открытия панели."""
    await message.answer(
        "🏠 <b>Панель администратора</b>\n\nВыберите раздел:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_menu")
async def admin_menu_callback(callback: CallbackQuery, admin: Admin) -> None:
    """Вернуться в главное меню."""
    await callback.message.answer(
        f"🏠 <b>Панель администратора</b>\n\nВыберите раздел:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(F.text == "👥 Пользователи")
async def show_users_list(message: Message) -> None:
    """Показать список пользователей."""
    users = await rq.get_all_users()

    if not users:
        await message.answer("📭 Пользователей пока нет.")
        return

    text = f"👥 <b>Пользователи ({len(users)})</b>\n\n"
    for i, user in enumerate(users[:10], 1):
        status = "✅" if user.received_bonus else "⏳"
        text += f"{i}. {status} <code>{user.tg_id}</code> - {user.full_name or 'Unknown'}"
        if user.username:
            text += f" (@{user.username})"
        text += f"\n   Баланс: {user.balance}₽\n"

    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📡 Серверы")
async def show_servers_list(message: Message) -> None:
    """Показать список серверов."""
    servers = await rq.get_all_servers()

    if not servers:
        await message.answer("📭 Серверов пока нет.\nНажмите «➕ Добавить сервер».")
        return

    text = f"📡 <b>Серверы ({len(servers)})</b>\n\n"
    for server in servers:
        status = "✅ Активен" if server.is_active else "❌ Отключён"
        text += f"🔹 <b>{server.name}</b>\n"
        text += f"   Локация: {server.location}\n"
        text += f"   URL: {server.api_url}\n"
        text += f"   Статус: {status}\n"
        if server.max_clients:
            text += f"   Макс. клиентов: {server.max_clients}\n"
        text += "\n"

    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "💳 Тарифы")
async def show_plans_list(message: Message) -> None:
    """Показать список тарифов."""
    plans = await rq.get_all_plans()

    if not plans:
        await message.answer("📭 Тарифов пока нет.")
        return

    text = f"💳 <b>Тарифные планы ({len(plans)})</b>\n\n"
    for plan in plans:
        status = "✅" if plan.is_active else "❌"
        traffic = "∞ Безлимит" if plan.data_limit_gb <= 0 else f"{plan.data_limit_gb} ГБ"
        text += f"{status} <b>{plan.name}</b>\n"
        text += f"   Цена: {plan.price}₽\n"
        text += f"   Срок: {plan.duration_days} дн.\n"
        text += f"   Трафик: {traffic}\n\n"

    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "📋 Подписки")
async def show_subscriptions_list(message: Message) -> None:
    """Показать список подписок."""
    # Получаем последние 10 подписок
    async with rq.async_session() as session:
        from sqlalchemy import select
        from app.database.models import Subscription
        result = await session.execute(
            select(Subscription).order_by(Subscription.created_at.desc()).limit(10)
        )
        subscriptions = list(result.scalars().all())

    if not subscriptions:
        await message.answer("📭 Подписок пока нет.")
        return

    text = f"📋 <b>Последние подписки ({len(subscriptions)})</b>\n\n"
    for sub in subscriptions:
        user = await session.get(rq.User, sub.user_id)
        user_name = user.full_name if user else f"User {sub.user_id}"
        text += f"🔹 {user_name}\n"
        text += f"   Email: {sub.email}\n"
        text += f"   Истекает: {sub.expires_at.strftime('%d.%m.%Y')}\n"
        status_value = sub.status.value if hasattr(sub.status, 'value') else sub.status
        text += f"   Статус: {status_value}\n\n"

    await message.answer(text, parse_mode="HTML")
