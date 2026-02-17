"""
Хендлеры для команды /start и реферальной системы.
"""
import logging

from aiogram import F, Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from app.database import requests as rq
from app.database.models import Plan, Server
from app.services.subscription import SubscriptionService
from app.services.referral import ReferralService
from app.keyboards import main_menu
from app.utils import MessageCleaner

logger = logging.getLogger(__name__)

router = Router()

BOT_USERNAME = "VPNLESS_VPN_BOT"


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    """
    Обработчик команды /start.
    
    Args:
        message: Сообщение от пользователя
    """
    referrer_id = None
    
    # Получаем аргументы команды (после /start)
    args = message.text.split() if message.text else []
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == message.from_user.id:
            referrer_id = None  # Нельзя пригласить самого себя

    # Регистрация пользователя
    is_new = await rq.add_user(
        tg_id=message.from_user.id,
        name=message.from_user.first_name,
        surname=message.from_user.last_name,
        user_tag=message.from_user.username,
        referrer_id=referrer_id
    )

    if is_new:
        await _handle_new_user(
            message=message,
            referrer_id=referrer_id
        )
    else:
        await message.answer(
            f"С возвращением, {message.from_user.first_name}!",
            reply_markup=main_menu
        )

    # Очистка старых сообщений
    await MessageCleaner.clear_old_messages(message.from_user.id, max_messages=2)


async def _handle_new_user(
    message: Message,
    referrer_id: int | None
) -> None:
    """
    Обработка нового пользователя.

    Args:
        message: Сообщение от пользователя
        referrer_id: ID реферера
    """
    msg = f"👋 Привет, {message.from_user.first_name}!\nДобро пожаловать в VPNLESS."

    # Получаем trial план и сервер
    trial_plan = await rq.get_trial_plan()
    server = await rq.get_active_server()

    if trial_plan and server:
        success, sub_link = await SubscriptionService.activate_trial(
            tg_id=message.from_user.id,
            trial_plan=trial_plan,
            server=server
        )

        if success and sub_link:
            msg += (
                f"\n\n🎁 **Вам начислен пробный период на 7 дней!**\n\n"
                f"Моя подписка: [Нажать]({sub_link})\n"
                f"Ваш ключ в профиле."
            )

    # Обработка реферала
    if referrer_id and server and trial_plan:
        bot = Bot.from_current()
        await ReferralService.process_referral(
            new_user_id=message.from_user.id,
            referrer_id=referrer_id,
            server=server,
            trial_plan=trial_plan,
            bot=bot
        )

    await message.answer(msg, reply_markup=main_menu, parse_mode="Markdown")


@router.callback_query(F.data == "ref_link")
async def show_ref_link(callback: CallbackQuery) -> None:
    """
    Показ реферальной ссылки пользователя.
    
    Args:
        callback: Callback query от пользователя
    """
    link = ReferralService.generate_ref_link(BOT_USERNAME, callback.from_user.id)
    
    await callback.message.answer(
        f"🔗 **Ваша реферальная ссылка:**\n`{link}`\n\n"
        f"Пригласите друга и получите 7 дней подписки бесплатно!",
        parse_mode="Markdown"
    )
    await callback.answer()
