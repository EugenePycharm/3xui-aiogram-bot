"""
Скрипт инициализации базы данных.
Создаёт таблицы, обновляет тарифы, добавляет сервер и администратора.
"""
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

# Добавляем корень проекта в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.models import create_tables, Plan, Admin, Server, async_session
from sqlalchemy import select, delete

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ожидаемые тарифы
EXPECTED_PLANS = [
    {"name": "Trial (Тестовый)", "price": 0.0, "duration_days": 7, "data_limit_gb": 15},
    {"name": "1 месяц - 70GB", "price": 85.0, "duration_days": 30, "data_limit_gb": 70},
    {"name": "1 месяц - Безлимит", "price": 100.0, "duration_days": 30, "data_limit_gb": 0},
    {"name": "6 месяцев - 900GB", "price": 479.0, "duration_days": 180, "data_limit_gb": 900},
    {"name": "6 месяцев - Безлимит", "price": 549.0, "duration_days": 180, "data_limit_gb": 0},
    {"name": "1 год - 2.5TB", "price": 859.0, "duration_days": 365, "data_limit_gb": 2500},
    {"name": "1 год - Безлимит", "price": 999.0, "duration_days": 365, "data_limit_gb": 0}
]


def _plans_match(existing_plans, expected_plans) -> bool:
    """Проверка соответствия тарифов ожидаемым."""
    if len(existing_plans) != len(expected_plans):
        return False
    
    existing_names = {p.name for p in existing_plans}
    expected_names = {p["name"] for p in expected_plans}
    
    return existing_names == expected_names


async def _update_plans(session):
    """Обновить тарифы в базе данных."""
    # Удаляем все существующие тарифы
    await session.execute(delete(Plan))
    
    # Добавляем новые
    for plan_data in EXPECTED_PLANS:
        plan = Plan(**plan_data)
        session.add(plan)
    
    await session.commit()
    logger.info(f"Обновлено {len(EXPECTED_PLANS)} тарифов.")


async def init_database():
    """Инициализация базы данных."""

    logger.info("Создание таблиц...")
    await create_tables()
    logger.info("Таблицы созданы успешно.")

    # Проверка и обновление тарифов
    async with async_session() as session:
        result = await session.execute(select(Plan))
        existing_plans = result.scalars().all()

        if not existing_plans:
            logger.info("Добавление тарифов...")
            await _update_plans(session)
        elif not _plans_match(existing_plans, EXPECTED_PLANS):
            logger.info("Тарифы не соответствуют ожидаемым. Обновление...")
            await _update_plans(session)
        else:
            logger.info(f"Тарифы актуальны ({len(existing_plans)} шт.).")

    # Проверка и создание первого сервера из .env (в отдельной сессии)
    async with async_session() as session:
        result = await session.execute(select(Server))
        existing_servers = result.scalars().all()

        server_url = os.getenv("SERVER_API_URL")
        server_username = os.getenv("SERVER_USERNAME")
        server_password = os.getenv("SERVER_PASSWORD")

        if server_url and server_username and server_password and not existing_servers:
            logger.info("Добавление первого сервера из переменных окружения...")
            # Извлекаем локацию из URL (или используем значение по умолчанию)
            location = os.getenv("SERVER_LOCATION", "Default")
            server_name = os.getenv("SERVER_NAME", "Server-1")
            max_clients = int(os.getenv("SERVER_MAX_CLIENTS", "50")) if os.getenv("SERVER_MAX_CLIENTS") else None

            server = Server(
                name=server_name,
                api_url=server_url,
                username=server_username,
                password=server_password,
                location=location,
                is_active=True,
                max_clients=max_clients
            )
            session.add(server)
            await session.commit()
            logger.info(f"Добавлен сервер: {server_name} ({location})")
        elif existing_servers:
            logger.info(f"Серверы уже существуют ({len(existing_servers)} шт.).")
        else:
            logger.warning("SERVER_API_URL, SERVER_USERNAME или SERVER_PASSWORD не указаны в .env")

    # Добавление администратора (если указан ADMIN_TELEGRAM_IDS)
    admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")

    if admin_ids_str:
        admin_ids = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]

        async with async_session() as session:
            for admin_id in admin_ids:
                # Проверяем, есть ли уже такой админ
                result = await session.execute(select(Admin).where(Admin.tg_id == admin_id))
                existing_admin = result.scalar_one_or_none()

                if not existing_admin:
                    admin = Admin(
                        tg_id=admin_id,
                        username=f"admin_{admin_id}",
                        is_active=True
                    )
                    session.add(admin)
                    logger.info(f"Добавлен администратор с ID: {admin_id}")
                else:
                    logger.info(f"Администратор с ID {admin_id} уже существует.")

            await session.commit()
    else:
        logger.warning("ADMIN_TELEGRAM_IDS не указан. Администраторы не добавлены.")
        logger.info("Добавьте администратора вручную: python add_admin.py <telegram_id>")

    logger.info("Инициализация базы данных завершена.")


if __name__ == "__main__":
    asyncio.run(init_database())
