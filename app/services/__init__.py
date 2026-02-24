"""
Пакет сервисов для бизнес-логики VPN бота.
"""
from app.services.subscription import SubscriptionService
from app.services.referral import ReferralService

__all__ = [
    "SubscriptionService",
    "ReferralService",
]
