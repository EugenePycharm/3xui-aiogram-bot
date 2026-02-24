"""
Хендлеры для создания подписки с кастомными параметрами.
"""
import logging
import uuid
from datetime import datetime, timedelta
from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from app.database import requests as rq
from app.database.models import Server, SubscriptionStatus
from app.api.three_x_ui import ThreeXUIClient
from app.utils.admin_utils import parse_date_input, parse_traffic_input, format_datetime, generate_uuid

logger = logging.getLogger(__name__)

router = Router()


# ==================== Создание подписки ====================

@router.message(F.text == "➕ Создать подписку")
async def start_create_subscription(message: Message, state: FSMContext) -> None:
    """Начать процесс создания подписки."""
    logger.info(f"Starting subscription creation for user {message.from_user.id}")
    
    await message.answer(
        "📝 <b>Создание подписки</b>\n\n"
        "Введите <b>Telegram ID</b> пользователя:\n"
        "(или отправьте /cancel для отмены)",
        parse_mode="HTML"
    )
    await state.set_state("admin_create_sub_user_id")
    logger.info(f"State set to admin_create_sub_user_id")


@router.message(F.text == "/cancel")
async def cancel_creation(message: Message, state: FSMContext) -> None:
    """Отменить создание подписки."""
    current_state = await state.get_state()
    if current_state and current_state.startswith("admin_create_sub"):
        await state.clear()
        await message.answer("❌ Создание подписки отменено.")
    else:
        # Пропускаем, если не в состоянии создания подписки
        return


@router.message()
async def create_subscription_fsm_handler(message: Message, state: FSMContext) -> None:
    """Универсальный хендлер для FSM создания подписки."""
    current_state = await state.get_state()
    
    logger.info(f"FSM handler called. State: {current_state}, Message: {message.text}")
    
    # Обработка ввода Telegram ID
    if current_state == "admin_create_sub_user_id":
        if not message.text.isdigit():
            await message.answer(
                f"❌ <code>{message.text}</code> не является числом.\n\n"
                "Введите корректный Telegram ID (только цифры):",
                parse_mode="HTML"
            )
            return

        tg_id = int(message.text)
        logger.info(f"Processing user ID: {tg_id}")

        # Проверяем пользователя
        user = await rq.get_user_by_tg_id(tg_id)
        if not user:
            await message.answer(
                f"❌ Пользователь с ID <code>{tg_id}</code> не найден.\n\n"
                "Введите корректный Telegram ID:",
                parse_mode="HTML"
            )
            return

        # Сохраняем в state
        await state.update_data(user_id=user.id, tg_id=tg_id, user_name=user.full_name)

        # Получаем активные серверы
        servers = await rq.get_all_servers()
        active_servers = [s for s in servers if s.is_active]

        if not active_servers:
            await message.answer("❌ Нет активных серверов. Сначала добавьте сервер.")
            await state.clear()
            return

        # Показываем клавиатуру с серверами
        builder = InlineKeyboardBuilder()
        for server in active_servers:
            builder.row(
                InlineKeyboardButton(
                    text=f"📡 {server.name} ({server.location})",
                    callback_data=f"admin_select_server_{server.id}"
                )
            )
        builder.row(
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")
        )

        await message.answer(
            f"✅ Пользователь: {user.full_name or 'Unknown'}\n\n"
            "Выберите сервер для подписки:",
            reply_markup=builder.as_markup()
        )
        await state.set_state("admin_create_sub_server")
        return

    # Обработка ввода лимита трафика
    if current_state == "admin_create_sub_traffic":
        logger.info(f"Received traffic limit: {message.text}")
        traffic_gb = parse_traffic_input(message.text)
        logger.info(f"Parsed traffic GB: {traffic_gb}")

        await state.update_data(traffic_gb=traffic_gb)

        # Показываем календарь для выбора даты
        await show_calendar(message, state)
        await state.set_state("admin_create_sub_date")
        return

    # Обработка ввода времени
    if current_state == "admin_create_sub_time":
        try:
            hours, minutes = map(int, message.text.strip().split(":"))
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError()

            data = await state.get_data()
            selected_date = data.get("selected_date", datetime.now())
            new_date = selected_date.replace(hour=hours, minute=minutes)

            await state.update_data(selected_date=new_date)

            # Показываем календарь снова
            await show_calendar(message, state)
            await state.set_state("admin_create_sub_date")

        except ValueError:
            await message.answer("❌ Неверный формат. Введите время в формате ЧЧ:ММ:")
        return


@router.callback_query(F.data.startswith("admin_select_server_"))
async def process_server_select(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора сервера."""
    server_id = int(callback.data.split("_")[-1])
    server = await rq.get_all_servers()
    server = next((s for s in server if s.id == server_id), None)

    if not server:
        await callback.answer("❌ Сервер не найден", show_alert=True)
        return

    data = await state.get_data()
    await state.update_data(server_id=server_id, server_name=server.name)

    await callback.message.answer(
        f"✅ Сервер: {server.name}\n\n"
        "Введите <b>лимит трафика в ГБ</b> (или 0 для безлимита):",
        parse_mode="HTML"
    )
    await state.set_state("admin_create_sub_traffic")
    await callback.answer()


async def show_calendar(message: Message, state: FSMContext) -> None:
    """Показать календарь для выбора даты."""
    data = await state.get_data()
    current_date = data.get("selected_date", datetime.now())

    # Генерируем клавиатуру календаря
    builder = InlineKeyboardBuilder()

    # Заголовок с месяцем и годом
    month_name = current_date.strftime("%B %Y")
    builder.row(
        InlineKeyboardButton(text=f"📅 {month_name}", callback_data="admin_calendar_title")
    )

    # Навигация по месяцам
    prev_month = current_date.replace(day=1) - timedelta(days=1)
    next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)

    builder.row(
        InlineKeyboardButton(text="⬅️ Пред. месяц", callback_data=f"admin_calendar_prev_{prev_month.strftime('%Y-%m')}"),
        InlineKeyboardButton(text="След. месяц ➡️", callback_data=f"admin_calendar_next_{next_month.strftime('%Y-%m')}"),
    )

    # Дни недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=d, callback_data="admin_calendar_wd") for d in weekdays])

    # Дни месяца
    year = current_date.year
    month = current_date.month
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, 28) + timedelta(days=4)
    last_day = last_day - timedelta(days=last_day.day)

    # Смещение для первого дня (0 = понедельник)
    first_day_offset = (first_day.weekday()) % 7

    # Пустые ячейки до первого дня
    week_row = []
    for _ in range(first_day_offset):
        week_row.append(InlineKeyboardButton(text="·", callback_data="admin_calendar_empty"))

    # Дни месяца
    for day in range(1, last_day.day + 1):
        date = datetime(year, month, day)
        is_today = date.date() == datetime.now().date()
        is_selected = data.get("selected_date") and date.date() == data["selected_date"].date()

        if is_selected:
            label = f"[{day}]"
        elif is_today:
            label = f"•{day}•"
        else:
            label = str(day)

        week_row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"admin_calendar_day_{date.strftime('%Y-%m-%d')}"
            )
        )

        if len(week_row) == 7:
            builder.row(*week_row)
            week_row = []

    # Добавляем оставшиеся дни
    if week_row:
        builder.row(*week_row)

    # Кнопки выбора времени
    builder.row(
        InlineKeyboardButton(text="⏰ Установить время", callback_data="admin_calendar_set_time"),
    )

    # Кнопка подтверждения
    selected = data.get("selected_date")
    if selected:
        builder.row(
            InlineKeyboardButton(
                text=f"✅ Выбрать {selected.strftime('%d.%m.%Y')}",
                callback_data="admin_calendar_confirm"
            )
        )

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")
    )

    await message.answer(
        "📅 <b>Выберите дату окончания подписки:</b>\n\n"
        "• — сегодня, [день] — выбрано",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_calendar_prev_"))
async def calendar_prev_month(callback: CallbackQuery, state: FSMContext) -> None:
    """Перейти к предыдущему месяцу."""
    year_month = callback.data.split("_")[-1]
    year, month = map(int, year_month.split("-"))
    new_date = datetime(year, month, 1)

    await state.update_data(selected_date=new_date)
    await show_calendar(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_calendar_next_"))
async def calendar_next_month(callback: CallbackQuery, state: FSMContext) -> None:
    """Перейти к следующему месяцу."""
    year_month = callback.data.split("_")[-1]
    year, month = map(int, year_month.split("-"))
    new_date = datetime(year, month, 1)

    await state.update_data(selected_date=new_date)
    await show_calendar(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_calendar_day_"))
async def calendar_select_day(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбрать день."""
    date_str = callback.data.split("_")[-1]
    year, month, day = map(int, date_str.split("-"))

    data = await state.get_data()
    selected_date = data.get("selected_date", datetime.now())
    new_date = datetime(year, month, day, selected_date.hour, selected_date.minute)

    await state.update_data(selected_date=new_date)
    await show_calendar(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "admin_calendar_set_time")
async def calendar_set_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Установить время."""
    await callback.message.answer(
        "⏰ Введите время в формате <b>ЧЧ:ММ</b> (например, 14:30):",
        parse_mode="HTML"
    )
    await state.set_state("admin_create_sub_time")
    await callback.answer()


@router.message()
async def process_time_input(message: Message, state: FSMContext) -> None:
    """Обработка ввода времени."""
    current_state = await state.get_state()
    
    if current_state != "admin_create_sub_time":
        return
    
    try:
        hours, minutes = map(int, message.text.strip().split(":"))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError()

        data = await state.get_data()
        selected_date = data.get("selected_date", datetime.now())
        new_date = selected_date.replace(hour=hours, minute=minutes)

        await state.update_data(selected_date=new_date)

        # Показываем календарь снова
        await show_calendar(message, state)
        await state.set_state("admin_create_sub_date")

    except ValueError:
        await message.answer("❌ Неверный формат. Введите время в формате ЧЧ:ММ:")


@router.callback_query(F.data == "admin_calendar_confirm")
async def calendar_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтвердить выбор даты."""
    data = await state.get_data()
    expires_at = data.get("selected_date")

    if not expires_at:
        await callback.answer("❌ Дата не выбрана", show_alert=True)
        return

    # Проверяем, что дата в будущем
    if expires_at <= datetime.now():
        await callback.answer("❌ Дата должна быть в будущем", show_alert=True)
        return

    await state.update_data(expires_at=expires_at)

    # Создаём подписку
    await create_subscription_final(callback.message, state)
    await callback.answer()


async def create_subscription_final(message: Message, state: FSMContext) -> None:
    """Финальное создание подписки."""
    data = await state.get_data()

    user_id = data.get("user_id")
    server_id = data.get("server_id")
    traffic_gb = data.get("traffic_gb", 0)
    expires_at = data.get("expires_at")

    # Получаем сервер
    servers = await rq.get_all_servers()
    server = next((s for s in servers if s.id == server_id), None)

    if not server:
        await message.answer("❌ Ошибка: сервер не найден")
        await state.clear()
        return

    # Подключаемся к 3x-ui
    client = ThreeXUIClient(server.api_url, server.username, server.password)

    if not await client.login():
        await message.answer(f"❌ Ошибка подключения к серверу {server.name}")
        await state.clear()
        await client.close()
        return

    # Получаем inbounds
    inbounds_resp = await client.get_inbounds()
    if not inbounds_resp.get("success"):
        await message.answer("❌ Ошибка получения inbounds")
        await state.clear()
        await client.close()
        return

    inbounds = inbounds_resp.get("obj", [])
    if not inbounds:
        await message.answer("❌ Нет доступных inbounds")
        await state.clear()
        await client.close()
        return

    target_inbound = inbounds[0]

    # Генерируем данные клиента
    email = f"admin_{uuid.uuid4().hex[:8]}"
    client_uuid = generate_uuid()
    expiry_time_ms = int(expires_at.timestamp() * 1000)
    total_bytes = int(traffic_gb * 1024 * 1024 * 1024) if traffic_gb > 0 else 0

    # Добавляем клиента в 3x-ui
    success, msg, _ = await client.add_client(
        inbound_id=target_inbound["id"],
        email=email,
        total_gb=traffic_gb,
        expiry_time=expiry_time_ms,
        enable=True,
        sub_id=email
    )

    if not success:
        await message.answer(f"❌ Ошибка добавления клиента: {msg}")
        await state.clear()
        await client.close()
        return

    # Генерируем ссылку
    from app.utils import generate_vless_link, get_subscription_link, get_port_from_stream, extract_base_host

    base_host = extract_base_host(server.api_url)
    port = get_port_from_stream(target_inbound.get("streamSettings", "{}"), default_port=443)
    vless_link = generate_vless_link(
        client_uuid, base_host, port, email,
        target_inbound.get("streamSettings")
    )

    # Создаём подписку в БД
    subscription = await rq.create_custom_subscription(
        user_id=user_id,
        server_id=server_id,
        uuid=client_uuid,
        email=email,
        inbound_id=target_inbound["id"],
        key_url=vless_link,
        expires_at=expires_at,
        data_limit_gb=traffic_gb
    )

    if subscription:
        sub_link = get_subscription_link(base_host, email)

        await message.answer(
            f"✅ <b>Подписка создана!</b>\n\n"
            f"👤 Пользователь: ID {user_id}\n"
            f"📡 Сервер: {server.name}\n"
            f"📊 Трафик: {traffic_gb} ГБ\n"
            f"📅 Истекает: {expires_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🔗 Ссылка: <code>{sub_link}</code>\n\n"
            f"VLESS ключ:\n<code>{vless_link}</code>",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Ошибка сохранения подписки в БД")

    await state.clear()
    await client.close()


@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена действия."""
    await state.clear()
    await callback.message.answer("❌ Отменено.")
    await callback.answer()
