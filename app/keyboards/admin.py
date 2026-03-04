"""
Клавиатуры для админ-бота.
"""

from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню админ-бота."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="👥 Пользователи"),
        KeyboardButton(text="📡 Серверы"),
    )
    builder.row(
        KeyboardButton(text="💳 Тарифы"),
        KeyboardButton(text="📋 Подписки"),
    )
    builder.row(
        KeyboardButton(text="➕ Создать подписку"),
        KeyboardButton(text="➕ Добавить сервер"),
    )
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)


def get_users_list_keyboard(users: list, page: int = 0) -> InlineKeyboardBuilder:
    """Клавиатура со списком пользователей."""
    builder = InlineKeyboardBuilder()

    for user in users:
        name = f"{user.full_name or 'Unknown'}"
        if user.username:
            name += f" (@{user.username})"
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {name}", callback_data=f"admin_user_{user.id}"
            )
        )

    # Пагинация
    if page > 0:
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"admin_users_page_{page - 1}"
            )
        )
    if len(users) == 10:  # Если есть ещё
        builder.row(
            InlineKeyboardButton(
                text="Вперёд ➡️", callback_data=f"admin_users_page_{page + 1}"
            )
        )

    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="admin_menu"))

    return builder


def get_user_actions_keyboard(user_id: int) -> InlineKeyboardBuilder:
    """Клавиатура действий с пользователем."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить баланс", callback_data=f"admin_edit_balance_{user_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить пользователя", callback_data=f"admin_delete_user_{user_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к списку", callback_data="admin_users_list"
        ),
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu"),
    )
    return builder


def get_servers_list_keyboard(servers: list) -> InlineKeyboardBuilder:
    """Клавиатура со списком серверов."""
    builder = InlineKeyboardBuilder()

    for server in servers:
        status = "✅" if server.is_active else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {server.name} ({server.location})",
                callback_data=f"admin_server_{server.id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить сервер", callback_data="admin_add_server"
        ),
    )
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="admin_menu"))

    return builder


def get_server_actions_keyboard(server_id: int) -> InlineKeyboardBuilder:
    """Клавиатура действий с сервером."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ Редактировать", callback_data=f"admin_edit_server_{server_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить", callback_data=f"admin_delete_server_{server_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к списку", callback_data="admin_servers_list"
        ),
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu"),
    )
    return builder


def get_plans_list_keyboard(plans: list) -> InlineKeyboardBuilder:
    """Клавиатура со списком тарифов."""
    builder = InlineKeyboardBuilder()

    for plan in plans:
        status = "✅" if plan.is_active else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {plan.name} - {plan.price}₽",
                callback_data=f"admin_plan_{plan.id}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="➕ Добавить тариф", callback_data="admin_add_plan"),
    )
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="admin_menu"))

    return builder


def get_plan_actions_keyboard(plan_id: int) -> InlineKeyboardBuilder:
    """Клавиатура действий с тарифом."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ Редактировать", callback_data=f"admin_edit_plan_{plan_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить", callback_data=f"admin_delete_plan_{plan_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к списку", callback_data="admin_plans_list"
        ),
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu"),
    )
    return builder


def get_subscriptions_list_keyboard(
    subscriptions: list, page: int = 0
) -> InlineKeyboardBuilder:
    """Клавиатура со списком подписок."""
    builder = InlineKeyboardBuilder()

    for sub in subscriptions:
        user_name = f"User {sub.user_id}"
        if hasattr(sub, "user") and sub.user:
            user_name = sub.user.full_name or "Unknown"
        builder.row(
            InlineKeyboardButton(
                text=f"📋 {user_name} | {sub.email}",
                callback_data=f"admin_subscription_{sub.id}",
            )
        )

    # Пагинация
    if page > 0:
        builder.row(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"admin_subs_page_{page - 1}"
            )
        )
    if len(subscriptions) == 10:
        builder.row(
            InlineKeyboardButton(
                text="Вперёд ➡️", callback_data=f"admin_subs_page_{page + 1}"
            )
        )

    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="admin_menu"))

    return builder


def get_subscription_actions_keyboard(
    subscription_id: int, user_id: int
) -> InlineKeyboardBuilder:
    """Клавиатура действий с подпиской."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ Продлить", callback_data=f"admin_extend_sub_{subscription_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить подписку",
            callback_data=f"admin_delete_sub_{subscription_id}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="👤 К пользователю", callback_data=f"admin_user_{user_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к списку", callback_data="admin_subscriptions_list"
        ),
        InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu"),
    )
    return builder


def get_cancel_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура с кнопкой отмены."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    return builder


def get_select_server_keyboard(servers: list) -> InlineKeyboardBuilder:
    """Клавиатура выбора сервера."""
    builder = InlineKeyboardBuilder()

    for server in servers:
        if server.is_active:
            builder.row(
                InlineKeyboardButton(
                    text=f"✅ {server.name} ({server.location})",
                    callback_data=f"admin_select_server_{server.id}",
                )
            )

    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))

    return builder


def get_select_user_keyboard(users: list, action: str) -> InlineKeyboardBuilder:
    """Клавиатура выбора пользователя для действия."""
    builder = InlineKeyboardBuilder()

    for user in users[:20]:  # Ограничим количество
        name = f"{user.full_name or 'Unknown'}"
        if user.username:
            name += f" (@{user.username})"
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {name}", callback_data=f"admin_{action}_user_{user.id}"
            )
        )

    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))

    return builder
