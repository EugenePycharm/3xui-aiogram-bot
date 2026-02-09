from datetime import datetime

from sqlalchemy import BigInteger, String, ForeignKey, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger, nullable=False, unique=True)
    user_tag: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(50))
    surname: Mapped[str] = mapped_column(String(50), nullable=True)

class Server(Base):
    __tablename__ = "servers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    location: Mapped[str] = mapped_column(String(50))

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(ForeignKey("users.tg_id"))
    server_name: Mapped[str] = mapped_column(ForeignKey("servers.name"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    ends_at: Mapped[datetime] = mapped_column(DateTime)

async def create_tables():
    async with engine.connect() as conn:  # connect() вместо begin() для DDL
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()