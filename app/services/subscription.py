"""
Сервис для управления подписками VPN.
Инкапсулирует бизнес-логику выдачи и управления подписками.
"""

import logging
import re
import uuid as uuid_module
from datetime import datetime, timedelta
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.api.three_x_ui import ThreeXUIClient
from app.database.models import Server, Plan, Subscription
from app.database import requests as rq
from app.utils import (
    generate_vless_link,
    get_subscription_link,
    get_port_from_stream,
    extract_base_host,
)

logger = logging.getLogger(__name__)


def _generate_safe_email(
    tg_id: int, plan: Optional[Plan] = None, suffix: str = ""
) -> str:
    """
    Генерация безопасного email для подписки (только латиница и цифры).

    Args:
        tg_id: Telegram ID пользователя
        plan: Тарифный план (опционально)
        suffix: Дополнительный суффикс (например, 'trial')

    Returns:
        Безопасный email для 3x-ui панели
    """
    # Преобразуем название плана в латиницу
    plan_slug = ""
    is_trial = False

    if plan:
        # Проверяем если это trial план
        if "Trial" in plan.name or "Тестовый" in plan.name:
            plan_slug = "trial"
            is_trial = True
            suffix = ""  # Не добавляем суффикс для trial
        else:
            plan_map = {
                "1 месяц": "1m",
                "6 месяцев": "6m",
                "1 год": "1y",
                "70GB": "70gb",
                "900GB": "900gb",
                "2.5TB": "2500gb",
                "2500": "2500gb",
                "Безлимит": "unlim",
            }
            plan_parts = []
            for key, value in plan_map.items():
                if key in plan.name:
                    plan_parts.append(value)
            plan_slug = "_".join(plan_parts) if plan_parts else "plan"

    # Генерируем уникальный ID
    unique_id = uuid_module.uuid4().hex[:8]

    # Формируем email: user_{tg_id}_{plan}_{unique_id}
    parts = [f"user_{tg_id}"]
    if plan_slug:
        parts.append(plan_slug)
    if suffix and not is_trial:
        parts.append(suffix)
    parts.append(unique_id)

    email = "_".join(parts)

    # Очищаем от любых не-ASCII символов (на всякий случай)
    email = re.sub(r"[^a-z0-9_]", "", email.lower())

    return email


class SubscriptionService:
    """Сервис для управления подписками."""

    @staticmethod
    async def issue_subscription(
        tg_id: int, plan: Plan, server: Server, bot: Bot, replace_existing: bool = True
    ) -> Tuple[bool, Optional[Subscription]]:
        """
        Выдача подписки пользователю.

        Если у пользователя есть активная подписка, она будет обновлена
        (вместо создания новой).

        Args:
            tg_id: Telegram ID пользователя
            plan: Тарифный план
            server: Сервер для подключения
            bot: Экземпляр бота
            replace_existing: Если True - обновлять существующую подписку

        Returns:
            (success, subscription) - кортеж успеха и подписки
        """
        # Проверяем существующую подписку
        existing_sub = None
        if replace_existing:
            existing_sub = await rq.get_user_subscription(tg_id)

        client = ThreeXUIClient(server.api_url, server.username, server.password)

        if not await client.login():
            logger.error(f"Не удалось подключиться к серверу {server.name}")
            await client.close()
            return False, None

        inbounds_resp = await client.get_inbounds()
        if not inbounds_resp.get("success"):
            logger.error(f"Не удалось получить inbounds: {inbounds_resp}")
            await client.close()
            return False, None

        inbounds = inbounds_resp.get("obj", [])
        if not inbounds:
            logger.error("Нет доступных inbounds на сервере")
            await client.close()
            return False, None

        target_inbound = inbounds[0]

        # Генерируем безопасный email для подписки (только латиница)
        email = _generate_safe_email(tg_id, plan)
        expiry_time = int(
            (datetime.now() + timedelta(days=plan.duration_days)).timestamp() * 1000
        )

        success, _, uuid = await client.add_client(
            inbound_id=target_inbound["id"],
            email=email,
            total_gb=plan.data_limit_gb,
            expiry_time=expiry_time,
            sub_id=email,
        )

        if not success:
            logger.error(f"Не удалось добавить клиента: {email}")
            await client.close()
            return False, None

        # Генерация ссылок
        base_host = extract_base_host(server.api_url)
        port = get_port_from_stream(
            target_inbound.get("streamSettings", "{}"), default_port=443
        )
        vless_link = generate_vless_link(
            uuid, base_host, port, email, target_inbound.get("streamSettings")
        )

        subscription = None

        if existing_sub and replace_existing:
            # Обновляем существующую подписку
            # Сначала удаляем старого клиента из 3x-ui
            await client.delete_client(existing_sub.inbound_id, existing_sub.uuid)

            # Обновляем запись в БД
            await rq.update_subscription_email(
                subscription_id=existing_sub.id,
                new_email=email,
                new_uuid=uuid,
                new_key_url=vless_link,
                new_inbound_id=target_inbound["id"],
            )

            # Обновляем план и срок
            await rq.update_subscription_plan(
                subscription_id=existing_sub.id,
                plan_id=plan.id,
                duration_days=plan.duration_days,
                data_limit_gb=plan.data_limit_gb,
            )

            # Получаем обновлённую подписку
            subscription = await rq.get_user_subscription(tg_id)

            logger.info(f"Подписка обновлена для пользователя {tg_id}")
        else:
            # Создаём новую подписку
            subscription = await rq.create_subscription(
                user_id=tg_id,
                server_id=server.id,
                plan_id=plan.id,
                uuid=uuid,
                email=email,
                inbound_id=target_inbound["id"],
                key_url=vless_link,
            )
            logger.info(f"Создана новая подписка для пользователя {tg_id}")

        await client.close()
        return True, subscription

    @staticmethod
    async def get_subscription_keyboard(
        subscription: Subscription,
    ) -> InlineKeyboardBuilder:
        """
        Создание клавиатуры с ссылками на подписку.

        Args:
            subscription: Объект подписки

        Returns:
            InlineKeyboardBuilder с кнопками
        """
        builder = InlineKeyboardBuilder()

        base_host = extract_base_host(subscription.server.api_url)
        sub_link = get_subscription_link(base_host, subscription.email)

        builder.row(InlineKeyboardButton(text="📥 Моя подписка", url=sub_link))
        builder.row(
            InlineKeyboardButton(
                text="🔑 Посмотреть мой ключ", callback_data="view_key"
            )
        )

        return builder

    @staticmethod
    async def activate_trial(
        tg_id: int, trial_plan: Plan, server: Server
    ) -> Tuple[bool, Optional[str]]:
        """
        Активация пробной подписки.

        Args:
            tg_id: Telegram ID пользователя
            trial_plan: Тариф trial
            server: Сервер для подключения

        Returns:
            (success, subscription_link) - кортеж успеха и ссылки на подписку
        """
        client = ThreeXUIClient(server.api_url, server.username, server.password)

        if not await client.login():
            await client.close()
            return False, None

        inbounds_resp = await client.get_inbounds()
        if not inbounds_resp.get("success"):
            await client.close()
            return False, None

        inbounds = inbounds_resp.get("obj", [])
        if not inbounds:
            await client.close()
            return False, None

        target_inbound = inbounds[0]

        # Генерируем безопасный email для trial подписки
        email = _generate_safe_email(tg_id, trial_plan, suffix="trial")
        expiry_time = int((datetime.now() + timedelta(days=7)).timestamp() * 1000)

        success, _, uuid = await client.add_client(
            inbound_id=target_inbound["id"],
            email=email,
            total_gb=trial_plan.data_limit_gb,
            expiry_time=expiry_time,
            sub_id=email,
        )

        if not success:
            await client.close()
            return False, None

        base_host = extract_base_host(server.api_url)
        port = get_port_from_stream(
            target_inbound.get("streamSettings", "{}"), default_port=443
        )
        vless_link = generate_vless_link(
            uuid, base_host, port, email, target_inbound.get("streamSettings")
        )

        await rq.create_subscription(
            user_id=tg_id,
            server_id=server.id,
            plan_id=trial_plan.id,
            uuid=uuid,
            email=email,
            inbound_id=target_inbound["id"],
            key_url=vless_link,
            is_trial=True,
        )

        sub_link = get_subscription_link(base_host, email)
        await client.close()

        return True, sub_link

    @staticmethod
    async def extend_user_subscription(
        user_id: int,
        days: int,
        server: Server,
        subscription: Subscription,
        plan: Optional[Plan] = None,
    ) -> bool:
        """
        Продление подписки пользователя.

        Args:
            user_id: ID пользователя в БД
            days: Количество дней для продления
            server: Сервер
            subscription: Подписка для продления
            plan: План (опционально, для обновления лимитов)

        Returns:
            True если успешно
        """
        client = ThreeXUIClient(server.api_url, server.username, server.password)

        if not await client.login():
            await client.close()
            return False

        new_expires_at = subscription.expires_at + timedelta(days=days)
        new_expiry_time_ms = int(new_expires_at.timestamp() * 1000)

        updated = await client.update_client(
            inbound_id=subscription.inbound_id,
            client_uuid=subscription.uuid,
            email=subscription.email,
            total_gb=plan.data_limit_gb if plan else 0,
            expiry_time=new_expiry_time_ms,
            enable=True,
            sub_id=subscription.email,
        )

        if updated:
            await rq.extend_subscription(subscription.id, days)

        await client.close()
        return updated
