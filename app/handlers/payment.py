"""
Хендлеры для обработки платежей.
"""

import logging

from aiogram import F, Router, Bot
from aiogram.types import PreCheckoutQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database import requests as rq
from app.database.models import Plan, PaymentStatus
from app.services.subscription import SubscriptionService
from app.utils import extract_base_host, get_subscription_link

logger = logging.getLogger(__name__)

router = Router()


@router.pre_checkout_query()
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery, bot: Bot) -> None:
    """
    Подтверждение pre-checkout запроса от Telegram.

    Args:
        pre_checkout_q: Объект pre-checkout запроса
        bot: Экземпляр бота
    """
    logger.debug(f"Received pre_checkout_query: {pre_checkout_q.id}")
    try:
        await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)
        logger.debug("Answered pre_checkout_query: OK")
    except Exception as e:
        logger.error(f"Failed to answer pre_checkout_query: {e}")


@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot) -> None:
    """
    Обработка успешного платежа.

    Args:
        message: Сообщение об успешном платеже
        bot: Экземпляр бота
    """
    payload = message.successful_payment.invoice_payload
    parts = payload.split(":")

    plan_id = int(parts[1])
    tg_id = int(parts[2])
    balance_used = float(parts[3]) if len(parts) > 3 else 0

    # Сумма платежа в рублях (копейки / 100)
    payment_amount = message.successful_payment.total_amount / 100
    # Общая сумма с учётом баланса
    total_amount = payment_amount + balance_used

    # Списываем баланс, который был использован как скидка
    if balance_used > 0:
        await rq.deduct_balance(tg_id, balance_used)

    # Получаем план для записи в payments
    async with rq.async_session() as session:
        plan = await session.get(Plan, plan_id)

    # Создаём запись о платеже в БД
    await rq.create_payment(
        user_id=tg_id,
        amount=total_amount,
        currency="RUB",
        status=PaymentStatus.SUCCEEDED,
        provider_id=message.successful_payment.telegram_payment_charge_id,
    )

    # Активируем подписку
    server = await rq.get_active_server()

    if server and plan:
        success, subscription = await SubscriptionService.issue_subscription(
            tg_id=tg_id,
            plan=plan,
            server=server,
            bot=bot,
            replace_existing=True,  # Обновляем существующую подписку
        )

        if success and subscription:
            # Отправляем уведомление об успешной активации
            base_host = extract_base_host(server.api_url)
            sub_link = get_subscription_link(base_host, subscription.email)

            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="📥 Моя подписка", url=sub_link))
            builder.row(
                InlineKeyboardButton(
                    text="🔑 Посмотреть мой ключ", callback_data="view_key"
                )
            )

            await message.answer(
                f"✅ **Подписка активирована!**\n\n"
                f"Тариф: {plan.name}\n"
                f"Сумма оплаты: {total_amount} RUB\n"
                f"Срок действия: {subscription.expires_at.strftime('%d.%m.%Y')}\n\n"
                f"Нажмите на кнопки ниже для доступа.",
                reply_markup=builder.as_markup(),
                parse_mode="Markdown",
            )
            return

    # Если ошибка
    await message.answer(
        "✅ Оплата прошла, но возникла ошибка при создании ключа. "
        "Обратитесь в поддержку."
    )
