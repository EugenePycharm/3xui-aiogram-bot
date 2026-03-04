"""
Сервис для управления реферальной программой.
Инкапсулирует логику начисления бонусов и вознаграждений.
"""

import logging
from typing import Optional

from aiogram import Bot

from app.database.models import Server, Plan, Subscription, User
from app.database import requests as rq
from app.services.subscription import SubscriptionService

logger = logging.getLogger(__name__)

# Константы реферальной программы
REFERRAL_BONUS_DAYS = 7  # Дней продления за реферала
REFERRAL_BONUS_RUB = 10  # Рублей на баланс если бонус уже получен


class ReferralService:
    """Сервис для управления реферальной программой."""

    @staticmethod
    async def process_referral(
        new_user_id: int,
        referrer_id: Optional[int],
        server: Optional[Server],
        trial_plan: Optional[Plan],
        bot: Bot,
    ) -> None:
        """
        Обработка реферальной ссылки при регистрации нового пользователя.

        Args:
            new_user_id: ID нового пользователя
            referrer_id: ID пригласившего (referrer)
            server: Активный сервер
            trial_plan: Trial план
            bot: Экземпляр бота
        """
        logger.info(
            f"process_referral: new_user={new_user_id}, referrer_id={referrer_id}"
        )

        if not referrer_id:
            logger.warning("process_referral: referrer_id не указан")
            return

        ref_user = await rq.select_user(referrer_id)
        if not ref_user:
            logger.warning(f"process_referral: реферер {referrer_id} не найден в БД")
            return

        logger.info(
            f"process_referral: реферер найден - tg_id={ref_user.tg_id}, received_bonus={ref_user.received_bonus}"
        )

        # Проверяем, получал ли реферер бонус ранее
        if ref_user.received_bonus:
            # Если уже получал бонус — начисляем деньги
            logger.info(
                f"process_referral: реферер {ref_user.tg_id} уже получил бонус, начисляем деньги"
            )
            await ReferralService._grant_balance_bonus(ref_user=ref_user, bot=bot)
            return

        # Если сервер и trial план доступны — пытаемся начислить бонус
        if server and trial_plan:
            logger.info(
                f"process_referral: начисление бонуса рефереру {ref_user.tg_id}"
            )
            await ReferralService._grant_subscription_bonus(
                ref_user=ref_user, server=server, trial_plan=trial_plan, bot=bot
            )
        else:
            # Нет сервера или trial плана — начисляем деньги
            logger.warning(
                f"process_referral: нет сервера или trial плана, начисляем деньги рефереру {ref_user.tg_id}"
            )
            await ReferralService._grant_balance_bonus(ref_user=ref_user, bot=bot)
            await rq.set_user_bonus_received(ref_user.id)

    @staticmethod
    async def _grant_subscription_bonus(
        ref_user: User, server: Server, trial_plan: Plan, bot: Bot
    ) -> None:
        """
        Начисление бонуса в виде продления подписки.

        Args:
            ref_user: Пользователь-реферер
            server: Сервер
            trial_plan: Trial план
            bot: Экземпляр бота
        """
        ref_sub = await rq.get_user_subscription(ref_user.tg_id)

        if not ref_sub:
            # Нет активной подписки — начисляем деньги на баланс
            logger.info(
                f"У реферера {ref_user.tg_id} нет подписки, начисляем денежный бонус"
            )
            await ReferralService._grant_balance_bonus(ref_user=ref_user, bot=bot)
            # Помечаем бонус как использованный
            await rq.set_user_bonus_received(ref_user.id)
            return

        success = await SubscriptionService.extend_user_subscription(
            user_id=ref_user.id,
            days=REFERRAL_BONUS_DAYS,
            server=server,
            subscription=ref_sub,
            plan=trial_plan,
        )

        if success:
            # Помечаем бонус как использованный
            await rq.set_user_bonus_received(ref_user.id)

            # Уведомляем реферера
            await ReferralService._notify_subscription_bonus(
                referrer_id=ref_user.tg_id, subscription=ref_sub, bot=bot
            )
        else:
            # Если продление не удалось, начисляем деньги
            logger.warning(
                f"Не удалось продлить подписку рефереру {ref_user.tg_id}, начисляем деньги"
            )
            await ReferralService._grant_balance_bonus(ref_user=ref_user, bot=bot)
            await rq.set_user_bonus_received(ref_user.id)

    @staticmethod
    async def _grant_balance_bonus(ref_user: User, bot: Bot) -> None:
        """
        Начисление денежного бонуса на баланс.

        Args:
            ref_user: Пользователь-реферер
            bot: Экземпляр бота
        """
        await rq.add_balance(ref_user.tg_id, REFERRAL_BONUS_RUB)

        try:
            await bot.send_message(
                ref_user.tg_id,
                f"🎉 По вашей ссылке зарегистрировался друг! "
                f"Вам начислено {REFERRAL_BONUS_RUB} рублей на баланс.",
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление о бонусе: {e}")

    @staticmethod
    async def _notify_subscription_bonus(
        referrer_id: int, subscription: Subscription, bot: Bot
    ) -> None:
        """
        Уведомление о продлении подписки.

        Args:
            referrer_id: ID реферера в Telegram
            subscription: Подписка
            bot: Экземпляр бота
        """
        try:
            base_host = (
                subscription.server.api_url.split("//")[1].split("/")[0].split(":")[0]
            )
            sub_link = f"https://{base_host}/egcPsGWuDm/{subscription.email}"

            await bot.send_message(
                referrer_id,
                f"🎉 По вашей ссылке зарегистрировался друг!\n"
                f"Ваша подписка продлена на {REFERRAL_BONUS_DAYS} дней.\n\n"
                f"Моя подписка: [Нажать]({sub_link})",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить уведомление о продлении: {e}")

    @staticmethod
    def generate_ref_link(bot_username: str, user_id: int) -> str:
        """
        Генерация реферальной ссылки.

        Args:
            bot_username: Юзернейм бота
            user_id: ID пользователя

        Returns:
            Реферальная ссылка
        """
        return f"https://t.me/{bot_username}?start={user_id}"

    @staticmethod
    async def get_referrals_count(user_id: int) -> int:
        """
        Получение количества приглашённых пользователей.

        Args:
            user_id: ID пользователя в БД

        Returns:
            Количество рефералов
        """
        return await rq.get_referrals_count(user_id)
