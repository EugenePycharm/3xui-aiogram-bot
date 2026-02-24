"""
Скрипт добавления сервера в базу данных.
Использует переменные окружения SERVER_*.
"""
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.models import async_session, Server
from sqlalchemy import select

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def add_server():
    """Добавить сервер из переменных окружения."""
    server_url = os.getenv("SERVER_API_URL")
    server_username = os.getenv("SERVER_USERNAME")
    server_password = os.getenv("SERVER_PASSWORD")

    if not server_url or not server_username or not server_password:
        logger.error("SERVER_API_URL, SERVER_USERNAME или SERVER_PASSWORD не указаны")
        return

    async with async_session() as session:
        # Проверяем существующие серверы
        result = await session.execute(select(Server))
        existing_servers = result.scalars().all()

        if existing_servers:
            logger.info(f"Серверы уже существуют ({len(existing_servers)} шт.):")
            for s in existing_servers:
                logger.info(f"  - {s.name} ({s.location})")
            return

        # Создаём новый сервер
        location = os.getenv("SERVER_LOCATION", "Default")
        server_name = os.getenv("SERVER_NAME", "Server-1")
        max_clients_str = os.getenv("SERVER_MAX_CLIENTS", "50")
        max_clients = int(max_clients_str) if max_clients_str.isdigit() else None

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

        logger.info(f"✅ Сервер добавлен: {server_name} ({location})")
        logger.info(f"   URL: {server_url}")
        logger.info(f"   Макс. клиентов: {max_clients or '∞'}")


if __name__ == "__main__":
    asyncio.run(add_server())
