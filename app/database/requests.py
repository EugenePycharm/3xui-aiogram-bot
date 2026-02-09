from app.database.models import async_session
from app.database.models import User, Server, Subscription
from sqlalchemy import select

async def add_user(tg_id:int, user_tag:str, name:str, surname:str) -> None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id==tg_id))
        if not user:
            session.add(User(tg_id=tg_id, user_tag=user_tag, name=name, surname=surname))
            await session.commit()

