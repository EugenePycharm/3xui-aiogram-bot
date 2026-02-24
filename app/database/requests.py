from app.database.models import async_session, User, Server, Plan, Subscription, SubscriptionStatus, Payment, PaymentStatus, Admin
from sqlalchemy import select, update, delete, func
from datetime import datetime, timedelta
from typing import List, Optional

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


async def get_servers_with_stats() -> list:
    """
    Получить все активные серверы с количеством подписок.

    Returns:
        Список кортежей (server, subscriptions_count)
    """
    from sqlalchemy import func
    async with async_session() as session:
        result = await session.execute(
            select(
                Server,
                func.count(Subscription.id).label('sub_count')
            )
            .outerjoin(Subscription, Server.id == Subscription.server_id)
            .where(Server.is_active == True)
            .group_by(Server.id)
            .order_by(Server.id)
        )
        return result.all()


async def get_subscription_count_for_server(server_id: int) -> int:
    """
    Получить количество активных подписок на сервере.

    Args:
        server_id: ID сервера

    Returns:
        Количество подписок
    """
    from sqlalchemy import func
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Subscription.id))
            .where(
                Subscription.server_id == server_id,
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        return result.scalar() or 0

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


# ==================== Admin Functions ====================

async def get_admin_by_tg_id(tg_id: int) -> Optional[Admin]:
    """Получить администратора по Telegram ID."""
    async with async_session() as session:
        return await session.scalar(select(Admin).where(Admin.tg_id == tg_id))


async def add_admin(tg_id: int, username: Optional[str] = None) -> Optional[Admin]:
    """Добавить нового администратора."""
    async with async_session() as session:
        # Проверяем, существует ли уже
        existing = await session.scalar(select(Admin).where(Admin.tg_id == tg_id))
        if existing:
            return existing

        new_admin = Admin(tg_id=tg_id, username=username)
        session.add(new_admin)
        await session.commit()
        return new_admin


async def get_all_users() -> List[User]:
    """Получить всех пользователей."""
    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.created_at.desc()))
        return list(result.scalars().all())


async def get_user_by_tg_id(tg_id: int) -> Optional[User]:
    """Получить пользователя по Telegram ID."""
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))


async def get_user_by_id(user_id: int) -> Optional[User]:
    """Получить пользователя по внутреннему ID."""
    async with async_session() as session:
        return await session.get(User, user_id)


async def delete_user_by_id(user_id: int) -> bool:
    """Удалить пользователя по ID (включая подписки и платежи)."""
    async with async_session() as session:
        # Сначала удаляем подписки
        await session.execute(delete(Subscription).where(Subscription.user_id == user_id))
        # Затем платежи
        await session.execute(delete(Payment).where(Payment.user_id == user_id))
        # И самого пользователя
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
        return True


async def update_user_balance(user_id: int, new_balance: float) -> bool:
    """Обновить баланс пользователя."""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(balance=new_balance)
        )
        await session.commit()
        return True


async def get_all_servers() -> List[Server]:
    """Получить все серверы."""
    async with async_session() as session:
        result = await session.execute(select(Server).order_by(Server.name))
        return list(result.scalars().all())


async def add_server(
    name: str,
    api_url: str,
    username: str,
    password: str,
    location: str,
    max_clients: Optional[int] = None
) -> Server:
    """Добавить новый сервер."""
    async with async_session() as session:
        server = Server(
            name=name,
            api_url=api_url,
            username=username,
            password=password,
            location=location,
            max_clients=max_clients
        )
        session.add(server)
        await session.commit()
        return server


async def update_server(
    server_id: int,
    name: Optional[str] = None,
    api_url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    location: Optional[str] = None,
    is_active: Optional[bool] = None,
    max_clients: Optional[int] = None
) -> bool:
    """Обновить данные сервера."""
    async with async_session() as session:
        server = await session.get(Server, server_id)
        if not server:
            return False

        if name is not None:
            server.name = name
        if api_url is not None:
            server.api_url = api_url
        if username is not None:
            server.username = username
        if password is not None:
            server.password = password
        if location is not None:
            server.location = location
        if is_active is not None:
            server.is_active = is_active
        if max_clients is not None:
            server.max_clients = max_clients

        await session.commit()
        return True


async def delete_server(server_id: int) -> bool:
    """Удалить сервер."""
    async with async_session() as session:
        await session.execute(delete(Server).where(Server.id == server_id))
        await session.commit()
        return True


async def get_all_plans() -> List[Plan]:
    """Получить все тарифные планы."""
    async with async_session() as session:
        result = await session.execute(select(Plan).order_by(Plan.price))
        return list(result.scalars().all())


async def add_plan(
    name: str,
    price: float,
    duration_days: int,
    data_limit_gb: int = 0,
    is_active: bool = True
) -> Plan:
    """Добавить новый тарифный план."""
    async with async_session() as session:
        plan = Plan(
            name=name,
            price=price,
            duration_days=duration_days,
            data_limit_gb=data_limit_gb,
            is_active=is_active
        )
        session.add(plan)
        await session.commit()
        return plan


async def update_plan(
    plan_id: int,
    name: Optional[str] = None,
    price: Optional[float] = None,
    duration_days: Optional[int] = None,
    data_limit_gb: Optional[int] = None,
    is_active: Optional[bool] = None
) -> bool:
    """Обновить тарифный план."""
    async with async_session() as session:
        plan = await session.get(Plan, plan_id)
        if not plan:
            return False

        if name is not None:
            plan.name = name
        if price is not None:
            plan.price = price
        if duration_days is not None:
            plan.duration_days = duration_days
        if data_limit_gb is not None:
            plan.data_limit_gb = data_limit_gb
        if is_active is not None:
            plan.is_active = is_active

        await session.commit()
        return True


async def delete_plan(plan_id: int) -> bool:
    """Удалить тарифный план."""
    async with async_session() as session:
        await session.execute(delete(Plan).where(Plan.id == plan_id))
        await session.commit()
        return True


async def get_subscription_by_id(subscription_id: int) -> Optional[Subscription]:
    """Получить подписку по ID."""
    async with async_session() as session:
        return await session.get(Subscription, subscription_id)


async def create_custom_subscription(
    user_id: int,
    server_id: int,
    uuid: str,
    email: str,
    inbound_id: int,
    key_url: str,
    expires_at: datetime,
    data_limit_gb: int = 0,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
) -> Optional[Subscription]:
    """Создать подписку с кастомными параметрами."""
    async with async_session() as session:
        subscription = Subscription(
            user_id=user_id,
            server_id=server_id,
            plan_id=1,  # Default plan, can be customized
            uuid=uuid,
            email=email,
            inbound_id=inbound_id,
            key_url=key_url,
            status=status,
            expires_at=expires_at
        )
        session.add(subscription)
        await session.commit()
        return subscription


async def delete_subscription(subscription_id: int) -> bool:
    """Удалить подписку."""
    async with async_session() as session:
        await session.execute(delete(Subscription).where(Subscription.id == subscription_id))
        await session.commit()
        return True
