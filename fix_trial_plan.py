import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import select

sys.path.append(os.getcwd())
load_dotenv()

from app.database.models import async_session, Plan

async def fix_trial():
    async with async_session() as session:
        # User said 15GB limit
        stmt = select(Plan).where(Plan.price == 0)
        result = await session.execute(stmt)
        trial = result.scalar()
        
        if trial:
            print(f"Updating trial plan {trial.name} (ID: {trial.id})")
            trial.data_limit_gb = 15
            trial.duration_days = 7
            await session.commit()
            print("Trial plan updated to 15GB, 7 days.")
        else:
            print("Trial plan not found. Creating one...")
            new_trial = Plan(
                name="Trial",
                description="Пробный период 7 дней",
                price=0,
                duration_days=7,
                data_limit_gb=15
            )
            session.add(new_trial)
            await session.commit()
            print("New Trial plan created.")

if __name__ == "__main__":
    asyncio.run(fix_trial())
