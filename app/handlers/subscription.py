"""
Хендлеры для покупки и управления подписками.
"""
import logging
import os
import json

from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message, LabeledPrice, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.database import requests as rq
from app.database.models import Plan, Server, PaymentStatus
from app.services.subscription import SubscriptionService
from app.keyboards import get_plans_keyboard
from app.utils import MessageCleaner, extract_base_host, get_subscription_link

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == '💳 Купить подписку')
async def buy_subscription(message: Message) -> None:
    """
    Показ списка тарифов для покупки.
    
    Args:
        message: Сообщение от пользователя
    """
    async with rq.async_session() as session:
        plans = (
            await session.scalars(
                select(Plan).where(Plan.price > 0).order_by(Plan.price)
            )
        ).all()

    # Очищаем старые сообщения о покупке
    await MessageCleaner.clear_old_messages(message.from_user.id, max_messages=1)

    await message.answer(
        "Выберите тариф:",
        reply_markup=await get_plans_keyboard(plans)
    )


@router.callback_query(F.data.startswith("buy_plan_"))
async def process_buy_plan(callback: CallbackQuery, bot: Bot) -> None:
    """
    Обработка выбора тарифа.
    
    Args:
        callback: Callback query от пользователя
        bot: Экземпляр бота
    """
    plan_id = int(callback.data.split("_")[2])

    user = await rq.select_user(callback.from_user.id)
    async with rq.async_session() as session:
        plan = await session.get(Plan, plan_id)

    if not plan:
        await callback.answer("Тариф не найден.", show_alert=True)
        return

    # Полная оплата с баланса
    if user.balance >= plan.price:
        await _pay_with_balance(
            callback=callback,
            user=user,
            plan=plan,
            bot=bot
        )
        return

    # Частичная оплата через YooKassa
    await _pay_with_yookassa(
        callback=callback,
        user=user,
        plan=plan,
        bot=bot
    )


async def _pay_with_balance(
    callback: CallbackQuery,
    user,
    plan: Plan,
    bot: Bot
) -> None:
    """
    Оплата подписки с баланса пользователя.

    Args:
        callback: Callback query
        user: Объект пользователя
        plan: Тарифный план
        bot: Экземпляр бота
    """
    await rq.deduct_balance(user.tg_id, plan.price)

    # Создаём запись о платеже в БД
    await rq.create_payment(
        user_id=user.id,
        amount=plan.price,
        currency="RUB",
        status=PaymentStatus.SUCCEEDED,
        provider_id=f"balance_payment_{user.tg_id}_{int(__import__('time').time())}"
    )

    server = await rq.get_active_server()
    if server:
        success, subscription = await SubscriptionService.issue_subscription(
            tg_id=user.tg_id,
            plan=plan,
            server=server,
            bot=bot,
            replace_existing=True
        )

        if success and subscription:
            # Отправляем уведомление об успешной активации
            base_host = extract_base_host(server.api_url)
            sub_link = get_subscription_link(base_host, subscription.email)
            
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="📥 Моя подписка", url=sub_link))
            builder.row(InlineKeyboardButton(text="🔑 Посмотреть мой ключ", callback_data="view_key"))
            
            await callback.message.answer(
                f"✅ **Подписка активирована!**\n\n"
                f"Тариф: {plan.name}\n"
                f"Сумма оплаты: {plan.price} RUB (с баланса)\n"
                f"Срок действия: {subscription.expires_at.strftime('%d.%m.%Y')}\n\n"
                f"Нажмите на кнопки ниже для доступа.",
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
            await callback.answer()
        else:
            await callback.message.answer(
                "⚠️ Ошибка при активации. Деньги списаны, обратитесь в поддержку."
            )


async def _pay_with_yookassa(
    callback: CallbackQuery,
    user,
    plan: Plan,
    bot: Bot
) -> None:
    """
    Оплата подписки через YooKassa (с доплатой).

    Args:
        callback: Callback query
        user: Объект пользователя
        plan: Тарифный план
        bot: Экземпляр бота
    """
    from aiogram.types import LabeledPrice

    amount_to_pay = plan.price - user.balance

    # Receipt data для YooKassa (фискализация)
    # Структура должна соответствовать требованиям ЮKassa
    receipt_data = {
        "receipt": {
            "items": [
                {
                    "description": f"VPN: {plan.name} (доплата)",
                    "quantity": 1,
                    "amount": {
                        "value": str(amount_to_pay),
                        "currency": "RUB"
                    },
                    "vat_code": 1,  # НДС по ставке 0%
                    "payment_mode": "full_payment",
                    "payment_subject": "service"
                }
            ],
            "tax_system_code": 1  # Общая система налогообложения
        }
    }

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Подписка {plan.name}",
            description=(
                f"Доплата за VPN. Использовано с баланса: {user.balance} RUB. "
                f"К оплате: {amount_to_pay} RUB."
            ),
            payload=f"vpn_payment:{plan.id}:{callback.from_user.id}:{user.balance}",
            provider_token=os.getenv("YOOKASSA_LIVE_TOKEN"),
            currency="RUB",
            prices=[
                LabeledPrice(
                    label=f"Доплата за {plan.name}",
                    amount=int(amount_to_pay * 100)
                )
            ],
            start_parameter="create_invoice_vpn_sub",
            is_flexible=False,
            need_email=True,
            send_email_to_provider=True,
            provider_data=json.dumps(receipt_data)
        )
    except Exception as e:
        await callback.answer(
            f"⚠️ Ошибка при создании платежа: {str(e)}",
            show_alert=True
        )
        return

    await callback.answer()
