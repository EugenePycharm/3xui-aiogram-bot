from app.database.models import async_session, User, Server, Plan, Subscription, SubscriptionStatus, Payment, PaymentStatus
from sqlalchemy import select, update
from datetime import datetime, timedelta

async def add_user(tg_id, name, surname, user_tag, referrer_id=None):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        
        if not user:
            new_user = User(tg_id=tg_id, full_name=f"{name} {surname or ''}".strip(), username=user_tag, referrer_id=referrer_id)
            session.add(new_user)
            await session.commit()
            return True # Created
        return False # Exists

async def add_balance(tg_id, amount):
    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_id == tg_id).values(balance=User.balance + amount)
        )
        await session.commit()

async def deduct_balance(tg_id, amount):
    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_id == tg_id).values(balance=User.balance - amount)
        )
        await session.commit()


async def select_user(tg_id):
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))

async def get_test_plan():
    async with async_session() as session:
        # Assuming plan 1 is standard or specific test plan
        return await session.scalar(select(Plan).where(Plan.price > 0).limit(1))

async def get_trial_plan():
    async with async_session() as session:
        return await session.scalar(select(Plan).where(Plan.price == 0).limit(1))

async def set_user_bonus_received(user_id):
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(received_bonus=True)
        )
        await session.commit()

async def get_active_server():
    async with async_session() as session:
        return await session.scalar(select(Server).where(Server.is_active == True))

async def get_user_subscription(user_id):
    async with async_session() as session:
        stmt = select(Subscription).where(
            Subscription.user_id == user_id, 
            Subscription.status == SubscriptionStatus.ACTIVE
        ).order_by(Subscription.expires_at.desc())
        return await session.scalar(stmt)

async def extend_subscription(subscription_id, days):
    async with async_session() as session:
        sub = await session.get(Subscription, subscription_id)
        if sub:
            sub.expires_at += timedelta(days=days)
            await session.commit()
            return True
        return False

async def create_subscription(user_id, server_id, plan_id, uuid, email, inbound_id, key_url, is_trial=False):
    async with async_session() as session:
        # Calculate expiry
        plan = await session.get(Plan, plan_id)
        if not plan:
            return None
        
        # If active sub exists, user might be extending or replacing. 
        # For simplicity, we just create a new one. The profile logic should show the latest active one.
        
        expires_at = datetime.now() + timedelta(days=plan.duration_days)
        
        new_sub = Subscription(
            user_id=user_id,
            server_id=server_id,
            plan_id=plan_id,
            uuid=uuid,
            email=email,
            inbound_id=inbound_id,
            key_url=key_url,
            status=SubscriptionStatus.ACTIVE,
            expires_at=expires_at
        )
        session.add(new_sub)
        await session.commit()
        return new_sub

async def get_referrals_count(user_id):
    async with async_session() as session:
        # This count might need a proper join or backref count, doing simple way
        # Since logic changed to just simple count
        # In real scaling app, use func.count
        from sqlalchemy import func
        result = await session.execute(select(func.count(User.id)).where(User.referrer_id == user_id))
        return result.scalar()


async def create_payment(
    user_id: int,
    amount: float,
    currency: str = "RUB",
    status: PaymentStatus = PaymentStatus.SUCCEEDED,
    provider_id: str = None
) -> Payment:
    """
    Создание записи о платеже.
    
    Args:
        user_id: ID пользователя в БД
        amount: Сумма платежа
        currency: Валюта
        status: Статус платежа
        provider_id: ID платежа в платёжной системе
    
    Returns:
        Объект Payment
    """
    async with async_session() as session:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            status=status,
            provider_id=provider_id
        )
        session.add(payment)
        await session.commit()
        return payment


async def update_subscription_email(
    subscription_id: int,
    new_email: str,
    new_uuid: str,
    new_key_url: str,
    new_inbound_id: int
) -> bool:
    """
    Обновление данных подписки (email, uuid, key_url, inbound_id).
    
    Args:
        subscription_id: ID подписки
        new_email: Новый email
        new_uuid: Новый UUID
        new_key_url: Новая ссылка ключа
        new_inbound_id: Новый inbound ID
    
    Returns:
        True если успешно
    """
    async with async_session() as session:
        sub = await session.get(Subscription, subscription_id)
        if sub:
            sub.email = new_email
            sub.uuid = new_uuid
            sub.key_url = new_key_url
            sub.inbound_id = new_inbound_id
            await session.commit()
            return True
        return False


async def update_subscription_plan(
    subscription_id: int,
    plan_id: int,
    duration_days: int,
    data_limit_gb: int
) -> bool:
    """
    Обновление плана подписки с продлением срока.
    
    Args:
        subscription_id: ID подписки
        plan_id: Новый ID плана
        duration_days: Количество дней для добавления
        data_limit_gb: Лимит данных в ГБ
    
    Returns:
        True если успешно
    """
    async with async_session() as session:
        sub = await session.get(Subscription, subscription_id)
        if sub:
            sub.plan_id = plan_id
            # Продлеваем с текущего момента, а не от старого срока
            sub.expires_at = datetime.now() + timedelta(days=duration_days)
            await session.commit()
            return True
        return False
