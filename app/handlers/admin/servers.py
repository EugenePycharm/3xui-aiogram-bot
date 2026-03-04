"""
Хендлеры для управления серверами.
"""
import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from app.database import requests as rq

logger = logging.getLogger(__name__)

router = Router()


# ==================== Добавление сервера ====================

@router.callback_query(F.data == "admin_add_server")
async def start_add_server(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать добавление сервера."""
    await state.clear()

    await callback.message.answer(
        "📡 <b>Добавление сервера</b>\n\n"
        "Введите <b>название сервера</b> (например, Netherlands-1):\n"
        "(или /cancel для отмены)",
        parse_mode="HTML"
    )
    await state.set_state("admin_add_server_name")
    await callback.answer()


@router.message()
async def process_server_name(message: Message, state: FSMContext) -> None:
    """Обработка названия сервера."""
    current_state = await state.get_state()
    if current_state != "admin_add_server_name":
        return
        
    await state.update_data(server_name=message.text.strip())

    await message.answer(
        "✅ Название сохранено.\n\n"
        "Введите <b>API URL</b> сервера (например, http://1.2.3.4:2053):",
        parse_mode="HTML"
    )
    await state.set_state("admin_add_server_url")


@router.message()
async def process_server_url(message: Message, state: FSMContext) -> None:
    """Обработка API URL сервера."""
    current_state = await state.get_state()
    if current_state != "admin_add_server_url":
        return
        
    url = message.text.strip()

    # Простая валидация
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer(
            "❌ URL должен начинаться с http:// или https://\n\n"
            "Введите корректный API URL:"
        )
        return

    await state.update_data(server_url=url)

    await message.answer(
        "✅ URL сохранён.\n\n"
        "Введите <b>имя пользователя</b> для панели 3x-ui:",
        parse_mode="HTML"
    )
    await state.set_state("admin_add_server_username")


@router.message()
async def process_server_username(message: Message, state: FSMContext) -> None:
    """Обработка имени пользователя."""
    current_state = await state.get_state()
    if current_state != "admin_add_server_username":
        return
        
    await state.update_data(server_username=message.text.strip())

    await message.answer(
        "✅ Имя пользователя сохранено.\n\n"
        "Введите <b>пароль</b> для панели 3x-ui:",
        parse_mode="HTML"
    )
    await state.set_state("admin_add_server_password")


@router.message()
async def process_server_password(message: Message, state: FSMContext) -> None:
    """Обработка пароля."""
    current_state = await state.get_state()
    if current_state != "admin_add_server_password":
        return
        
    await state.update_data(server_password=message.text.strip())

    await message.answer(
        "✅ Пароль сохранён.\n\n"
        "Введите <b>локацию</b> сервера (например, Netherlands, Germany):",
        parse_mode="HTML"
    )
    await state.set_state("admin_add_server_location")


@router.message()
async def process_server_location(message: Message, state: FSMContext) -> None:
    """Обработка локации."""
    current_state = await state.get_state()
    if current_state != "admin_add_server_location":
        return
        
    await state.update_data(server_location=message.text.strip())

    await message.answer(
        "✅ Локация сохранена.\n\n"
        "Введите <b>максимальное количество клиентов</b> (или 0 для безлимита):",
        parse_mode="HTML"
    )
    await state.set_state("admin_add_server_max_clients")


@router.message()
async def process_server_max_clients(message: Message, state: FSMContext) -> None:
    """Обработка максимального количества клиентов."""
    current_state = await state.get_state()
    if current_state != "admin_add_server_max_clients":
        return
        
    try:
        max_clients = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректное число:")
        return

    data = await state.get_data()

    # Добавляем сервер в БД
    server = await rq.add_server(
        name=data["server_name"],
        api_url=data["server_url"],
        username=data["server_username"],
        password=data["server_password"],
        location=data["server_location"],
        max_clients=max_clients if max_clients > 0 else None
    )

    if server:
        # Проверяем подключение к серверу
        from app.api.three_x_ui import ThreeXUIClient

        client = ThreeXUIClient(server.api_url, server.username, server.password)
        login_success = await client.login()
        await client.close()

        status = "✅ Подключение успешно" if login_success else "⚠️ Ошибка подключения"

        await message.answer(
            f"✅ <b>Сервер добавлен!</b>\n\n"
            f"📡 Название: {server.name}\n"
            f"🌍 Локация: {server.location}\n"
            f"🔗 URL: {server.api_url}\n"
            f"👥 Макс. клиентов: {server.max_clients or '∞'}\n"
            f"📊 Статус: {status}",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Ошибка при добавлении сервера.")

    await state.clear()


# ==================== Карточка сервера ====================

@router.callback_query(F.data.startswith("admin_server_"))
async def show_server_card(callback: CallbackQuery) -> None:
    """Показать карточку сервера."""
    try:
        server_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    servers = await rq.get_all_servers()
    server = next((s for s in servers if s.id == server_id), None)

    if not server:
        await callback.answer("❌ Сервер не найден", show_alert=True)
        return

    # Проверяем подключение
    from app.api.three_x_ui import ThreeXUIClient
    client = ThreeXUIClient(server.api_url, server.username, server.password)
    login_success = await client.login()
    inbounds = await client.get_inbounds() if login_success else None
    await client.close()

    status = "✅ Активен" if server.is_active else "❌ Отключён"
    connection = "✅ Подключено" if login_success else "❌ Ошибка"

    text = "📡 <b>Карточка сервера</b>\n\n"
    text += f"<b>ID:</b> <code>{server.id}</code>\n"
    text += f"<b>Название:</b> {server.name}\n"
    text += f"<b>Локация:</b> {server.location}\n"
    text += f"<b>API URL:</b> <code>{server.api_url}</code>\n"
    text += f"<b>Пользователь:</b> {server.username}\n"
    text += f"<b>Статус:</b> {status}\n"
    text += f"<b>Подключение:</b> {connection}\n"

    if server.max_clients:
        text += f"<b>Макс. клиентов:</b> {server.max_clients}\n"

    if inbounds and inbounds.get("success"):
        inbounds_list = inbounds.get("obj", [])
        text += f"\n📊 <b>Inbounds ({len(inbounds_list)})</b>\n"
        for inbound in inbounds_list[:5]:
            text += f"  • {inbound.get('tag', 'Unknown')} "
            text += f"({inbound.get('port', '?')} port)\n"

    # Клавиатура действий
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"admin_edit_server_{server_id}"),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔘 Включить" if not server.is_active else "🔘 Выключить",
            callback_data=f"admin_toggle_server_{server_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_delete_server_confirm_{server_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_servers_list"),
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu"),
    )

    await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# ==================== Редактирование сервера ====================

@router.callback_query(F.data.startswith("admin_edit_server_"))
async def start_edit_server(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать редактирование сервера."""
    try:
        server_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    servers = await rq.get_all_servers()
    server = next((s for s in servers if s.id == server_id), None)

    if not server:
        await callback.answer("❌ Сервер не найден", show_alert=True)
        return

    await state.update_data(edit_server_id=server_id)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Название", callback_data="admin_edit_server_name"),
        InlineKeyboardButton(text="URL", callback_data="admin_edit_server_url"),
    )
    builder.row(
        InlineKeyboardButton(text="Логин", callback_data="admin_edit_server_username"),
        InlineKeyboardButton(text="Пароль", callback_data="admin_edit_server_password"),
    )
    builder.row(
        InlineKeyboardButton(text="Локация", callback_data="admin_edit_server_location"),
        InlineKeyboardButton(text="Макс. клиентов", callback_data="admin_edit_server_max"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin_server_{server_id}"),
    )

    await callback.message.answer(
        f"✏️ <b>Редактирование сервера</b>\n\n"
        f"Текущее название: {server.name}\n\n"
        f"Выберите поле для редактирования:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state("admin_edit_server_select")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_server_"))
async def edit_server_field(callback: CallbackQuery, state: FSMContext) -> None:
    """Редактирование поля сервера."""
    field = callback.data.replace("admin_edit_server_", "")

    if field in ["name", "url", "username", "password", "location", "max"]:
        await state.update_data(edit_server_field=field)

        field_names = {
            "name": "название",
            "url": "API URL",
            "username": "имя пользователя",
            "password": "пароль",
            "location": "локацию",
            "max": "макс. клиентов"
        }

        await callback.message.answer(
            f"Введите новое значение для поля <b>{field_names.get(field, field)}</b>:",
            parse_mode="HTML"
        )
        await state.set_state("admin_edit_server_value")
        await callback.answer()


@router.message()
async def process_edit_server_value(message: Message, state: FSMContext) -> None:
    """Обработка нового значения поля сервера."""
    current_state = await state.get_state()
    if current_state != "admin_edit_server_value":
        return
    
    data = await state.get_data()
    server_id = data.get("edit_server_id")
    field = data.get("edit_server_field")

    if not server_id or not field:
        await message.answer("❌ Ошибка: данные не найдены")
        await state.clear()
        return

    new_value = message.text.strip()

    # Маппинг полей
    field_map = {
        "name": "name",
        "url": "api_url",
        "username": "username",
        "password": "password",
        "location": "location",
        "max": "max_clients"
    }

    kwargs = {field_map[field]: new_value}

    # Для max_clients конвертируем в int
    if field == "max":
        try:
            kwargs["max_clients"] = int(new_value) if int(new_value) > 0 else None
        except ValueError:
            await message.answer("❌ Введите корректное число:")
            return

    success = await rq.update_server(server_id, **kwargs)

    if success:
        await message.answer("✅ Поле обновлено!")
    else:
        await message.answer("❌ Ошибка при обновлении.")

    await state.clear()


@router.callback_query(F.data.startswith("admin_toggle_server_"))
async def toggle_server(callback: CallbackQuery) -> None:
    """Включить/выключить сервер."""
    try:
        server_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    servers = await rq.get_all_servers()
    server = next((s for s in servers if s.id == server_id), None)

    if not server:
        await callback.answer("❌ Сервер не найден", show_alert=True)
        return

    new_status = not server.is_active
    await rq.update_server(server_id, is_active=new_status)

    await callback.message.answer(
        f"✅ Сервер <b>{server.name}</b> {'включён' if new_status else 'выключен'}.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_server_confirm_"))
async def confirm_delete_server(callback: CallbackQuery) -> None:
    """Подтверждение удаления сервера."""
    try:
        server_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    servers = await rq.get_all_servers()
    server = next((s for s in servers if s.id == server_id), None)

    if not server:
        await callback.answer("❌ Сервер не найден", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❗️ Да, удалить", callback_data=f"admin_delete_server_exec_{server_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_server_{server_id}"),
    )

    await callback.message.answer(
        f"⚠️ <b>Удаление сервера</b>\n\n"
        f"Вы уверены, что хотите удалить сервер:\n"
        f"{server.name}?\n\n"
        f"⚠️ Все связанные подписки станут нерабочими!",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_server_exec_"))
async def execute_delete_server(callback: CallbackQuery) -> None:
    """Удаление сервера."""
    try:
        server_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    servers = await rq.get_all_servers()
    server = next((s for s in servers if s.id == server_id), None)

    if not server:
        await callback.answer("❌ Сервер не найден", show_alert=True)
        return

    server_name = server.name
    await rq.delete_server(server_id)

    await callback.message.answer(f"✅ Сервер <b>{server_name}</b> удалён.", parse_mode="HTML")
    await callback.answer()
