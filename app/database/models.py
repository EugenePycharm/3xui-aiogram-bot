from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import BigInteger, String, ForeignKey, DateTime, Boolean, DECIMAL, Integer, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

# Enums
class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    BANNED = "banned"
    PENDING = "pending"

class PaymentStatus(str, PyEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(10, 2), default=0.00)
    referrer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    received_bonus: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="user")
    payments: Mapped[List["Payment"]] = relationship(back_populates="user")
    referrer: Mapped[Optional["User"]] = relationship("User", remote_side=[id], backref="referrals")

class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    api_url: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., http://1.2.3.4:2053
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., "Netherlands"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_clients: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="server")

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., "Basic - 1 Month"
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    data_limit_gb: Mapped[int] = mapped_column(Integer, default=0) # 0 for unlimited
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="plan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False) # VLESS UUID
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False) # 3x-ui identifier
    inbound_id: Mapped[int] = mapped_column(Integer, nullable=False) # 3x-ui inbound ID
    key_url: Mapped[str] = mapped_column(String, nullable=True) # Full VLESS link
    
    status: Mapped[SubscriptionStatus] = mapped_column(String(20), default=SubscriptionStatus.PENDING)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscriptions")
    server: Mapped["Server"] = relationship(back_populates="subscriptions", lazy="joined")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    status: Mapped[PaymentStatus] = mapped_column(String(20), default=PaymentStatus.PENDING)
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # e.g. PaymentIntentNullable

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="payments")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
