"""
Хендлеры для управления пользователями.
"""
import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from app.database import requests as rq
from app.database.models import Admin

logger = logging.getLogger(__name__)

router = Router()


# ==================== Просмотр пользователей ====================

@router.callback_query(F.data == "admin_users_list")
async def show_users_list_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать список пользователей (callback)."""
    await state.clear()
    users = await rq.get_all_users()

    if not users:
        await callback.message.answer("📭 Пользователей пока нет.")
        await callback.answer()
        return

    text = f"👥 <b>Пользователи ({len(users)})</b>\n\n"
    for i, user in enumerate(users[:10], 1):
        status = "✅" if user.received_bonus else "⏳"
        text += f"{i}. {status} <code>{user.tg_id}</code> - {user.full_name or 'Unknown'}"
        if user.username:
            text += f" (@{user.username})"
        text += f"\n   Баланс: {user.balance}₽\n"

    builder = InlineKeyboardBuilder()
    for user in users[:10]:
        name = f"{user.full_name or 'Unknown'}"[:20]
        if user.username:
            name = f"@{user.username}"
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {name}",
                callback_data=f"admin_user_{user.id}"
            )
        )

    if len(users) > 10:
        builder.row(
            InlineKeyboardButton(text="Всех в меню", callback_data="admin_users_all")
        )

    builder.row(
        InlineKeyboardButton(text="🔙 В меню", callback_data="admin_menu")
    )

    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_users_all")
async def show_all_users(callback: CallbackQuery) -> None:
    """Показать всех пользователей."""
    users = await rq.get_all_users()

    text = f"👥 <b>Все пользователи ({len(users)})</b>\n\n"
    for i, user in enumerate(users, 1):
        status = "✅" if user.received_bonus else "⏳"
        text += f"{i}. {status} <code>{user.tg_id}</code> - {user.full_name or 'Unknown'}"
        if user.username:
            text += f" (@{user.username})"
        text += f" | Баланс: {user.balance}₽\n"

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


# ==================== Карточка пользователя ====================

@router.callback_query(F.data.startswith("admin_user_"))
async def show_user_card(callback: CallbackQuery) -> None:
    """Показать карточку пользователя."""
    try:
        user_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    user = await rq.get_user_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    # Получаем подписки пользователя
    async with rq.async_session() as session:
        from sqlalchemy import select
        from app.database.models import Subscription
        result = await session.execute(
            select(rq.Subscription).where(rq.Subscription.user_id == user_id)
            .order_by(rq.Subscription.created_at.desc())
        )
        subscriptions = list(result.scalars().all())

    # Получаем рефералов
    async with rq.async_session() as session:
        from sqlalchemy import select, func
        ref_count = await session.scalar(
            select(func.count(rq.User.id)).where(rq.User.referrer_id == user_id)
        )

    text = f"👤 <b>Карточка пользователя</b>\n\n"
    text += f"<b>ID:</b> <code>{user.tg_id}</code>\n"
    text += f"<b>Имя:</b> {user.full_name or 'Unknown'}\n"
    if user.username:
        text += f"<b>Username:</b> @{user.username}\n"
    text += f"<b>Баланс:</b> {user.balance}₽\n"
    text += f"<b>Бонус получен:</b> {'✅ Да' if user.received_bonus else '❌ Нет'}\n"
    text += f"<b>Рефералов:</b> {ref_count or 0}\n"
    text += f"<b>Зарегистрирован:</b> {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"

    if subscriptions:
        text += f"\n📋 <b>Подписки ({len(subscriptions)})</b>\n"
        for sub in subscriptions[:3]:
            status_emoji = "✅" if sub.status == SubscriptionStatus.ACTIVE else "❌"
            text += f"   {status_emoji} {sub.email}\n"
            text += f"       до {sub.expires_at.strftime('%d.%m.%Y')}\n"
    else:
        text += "\n📭 Подписок нет"

    # Клавиатура действий
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить баланс", callback_data=f"admin_edit_balance_{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Все подписки", callback_data=f"admin_user_subs_{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить пользователя", callback_data=f"admin_delete_user_confirm_{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users_list"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu"),
    )

    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# ==================== Редактирование баланса ====================

@router.callback_query(F.data.startswith("admin_edit_balance_"))
async def start_edit_balance(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать редактирование баланса."""
    try:
        user_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    user = await rq.get_user_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    await state.update_data(edit_balance_user_id=user_id)

    await callback.message.answer(
        f"✏️ <b>Изменение баланса</b>\n\n"
        f"Пользователь: {user.full_name or 'Unknown'}\n"
        f"Текущий баланс: {user.balance}₽\n\n"
        f"Введите <b>новый баланс</b> (число):\n"
        f"(или используйте +100 / -50 для изменения)",
        parse_mode="HTML"
    )
    await state.set_state("admin_edit_balance_value")
    await callback.answer()


@router.message()
async def process_edit_balance(message: Message, state: FSMContext) -> None:
    """Обработка нового баланса."""
    current_state = await state.get_state()
    if current_state != "admin_edit_balance_value":
        return
    
    data = await state.get_data()
    user_id = data.get("edit_balance_user_id")

    if not user_id:
        await message.answer("❌ Ошибка: пользователь не указан")
        await state.clear()
        return

    try:
        text = message.text.strip()
        if text.startswith("+"):
            # Добавляем к балансу
            change = float(text[1:])
            user = await rq.get_user_by_id(user_id)
            new_balance = float(user.balance) + change
        elif text.startswith("-"):
            # Вычитаем из баланса
            change = float(text[1:])
            user = await rq.get_user_by_id(user_id)
            new_balance = float(user.balance) - change
        else:
            # Устанавливаем новый баланс
            new_balance = float(text)

        await rq.update_user_balance(user_id, new_balance)

        user = await rq.get_user_by_id(user_id)
        await message.answer(
            f"✅ Баланс изменён!\n\n"
            f"Новый баланс: <b>{new_balance}₽</b>",
            parse_mode="HTML"
        )

    except ValueError:
        await message.answer("❌ Введите корректное число (например, 500 или +100 или -50)")
        return

    await state.clear()


# ==================== Удаление пользователя ====================

@router.callback_query(F.data.startswith("admin_delete_user_confirm_"))
async def confirm_delete_user(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтверждение удаления пользователя."""
    try:
        user_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    user = await rq.get_user_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❗️ Да, удалить", callback_data=f"admin_delete_user_exec_{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_user_{user_id}"),
    )

    await callback.message.answer(
        f"⚠️ <b>Удаление пользователя</b>\n\n"
        f"Вы уверены, что хотите удалить пользователя:\n"
        f"{user.full_name or 'Unknown'} (ID: {user.tg_id})?\n\n"
        f"Это действие удалит:\n"
        f"• Все подписки (и клиентов в 3x-ui)\n"
        f"• Историю платежей\n"
        f"• Данные пользователя",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_user_exec_"))
async def execute_delete_user(callback: CallbackQuery) -> None:
    """Удаление пользователя."""
    try:
        user_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    user = await rq.get_user_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    # Получаем подписки для удаления из 3x-ui
    async with rq.async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(rq.Subscription).where(rq.Subscription.user_id == user_id)
        )
        subscriptions = list(result.scalars().all())

    # Удаляем клиентов из 3x-ui
    for sub in subscriptions:
        server = await session.get(rq.Server, sub.server_id)
        if server:
            from app.api.three_x_ui import ThreeXUIClient
            client = ThreeXUIClient(server.api_url, server.username, server.password)
            if await client.login():
                await client.delete_client(sub.inbound_id, sub.uuid)
                await client.close()

    # Удаляем из БД
    await rq.delete_user_by_id(user_id)

    await callback.message.answer(f"✅ Пользователь {user.full_name or 'Unknown'} удалён.")
    await callback.answer()


# ==================== Подписки пользователя ====================

@router.callback_query(F.data.startswith("admin_user_subs_"))
async def show_user_subscriptions(callback: CallbackQuery) -> None:
    """Показать подписки пользователя."""
    try:
        user_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    user = await rq.get_user_by_id(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    async with rq.async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(rq.Subscription).where(rq.Subscription.user_id == user_id)
            .order_by(rq.Subscription.created_at.desc())
        )
        subscriptions = list(result.scalars().all())

    if not subscriptions:
        await callback.message.answer("📭 У пользователя нет подписок.")
        await callback.answer()
        return

    text = f"📋 <b>Подписки пользователя</b>\n\n"
    text += f"Пользователь: {user.full_name or 'Unknown'}\n\n"

    for sub in subscriptions:
        status_val = sub.status.value if hasattr(sub.status, 'value') else sub.status
        status_emoji = "✅" if status_val == "active" else "❌"
        text += f"{status_emoji} <b>{sub.email}</b>\n"
        text += f"    Сервер ID: {sub.server_id}\n"
        text += f"    Истекает: {sub.expires_at.strftime('%d.%m.%Y')}\n"
        text += f"    Статус: {status_val}\n\n"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 К пользователю", callback_data=f"admin_user_{user_id}"),
    )

    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()
