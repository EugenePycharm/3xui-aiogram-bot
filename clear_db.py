import asyncio
from typing import Dict, List

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.database.models import async_session, Subscription, Server, User, Payment
from app.api.three_x_ui import ThreeXUIClient


async def remove_subscriptions_from_3xui() -> None:
    """
    Проходит по всем подпискам в БД и пытается удалить
    соответствующих клиентов из панелей 3x-ui.
    """
    async with async_session() as session:
        result = await session.execute(
            select(Subscription).options(selectinload(Subscription.server))
        )
        subscriptions: List[Subscription] = result.scalars().all()

        if not subscriptions:
            print("В БД нет подписок для удаления из 3x-ui.")
            return

        # Группируем подписки по серверу, чтобы переиспользовать соединение
        subs_by_server: Dict[int, List[Subscription]] = {}
        for sub in subscriptions:
            if not sub.server:
                # На всякий случай пропускаем, если у подписки нет связанного сервера
                continue
            subs_by_server.setdefault(sub.server.id, []).append(sub)

        for server_id, subs in subs_by_server.items():
            server: Server = subs[0].server
            print(f"\nОбработка сервера {server.name} ({server.api_url}), подписок: {len(subs)}")

            client = ThreeXUIClient(server.api_url, server.username, server.password)
            logged_in = await client.login()
            if not logged_in:
                print(f"❌ Не удалось авторизоваться в 3x-ui для сервера {server.name}, пропускаю его подписки.")
                await client.close()
                continue

            for sub in subs:
                try:
                    ok = await client.delete_client(sub.inbound_id, sub.uuid)
                    if ok:
                        print(f"  ✅ Удалён клиент из 3x-ui: user_id={sub.user_id}, uuid={sub.uuid}")
                    else:
                        print(f"  ⚠️ Не удалось удалить клиента в 3x-ui: user_id={sub.user_id}, uuid={sub.uuid}")
                except Exception as e:
                    print(f"  ⚠️ Ошибка при удалении клиента в 3x-ui (uuid={sub.uuid}): {e}")

            await client.close()


async def clear_database() -> None:
    """
    Очищает основные таблицы БД:
    - Подписки
    - Платежи
    - Пользователи

    Серверы и тарифы (plans/servers) считаем конфигурацией и не трогаем.
    """
    async with async_session() as session:
        # Сначала удаляем зависимые сущности
        await session.execute(delete(Subscription))
        await session.execute(delete(Payment))
        await session.execute(delete(User))
        await session.commit()

    print("\nБаза данных очищена (users, payments, subscriptions).")


async def main() -> None:
    print("⚠️ ВНИМАНИЕ: будет выполнена очистка БД и попытка удалить все подписки из 3x-ui.")

    # 1. Удаляем клиентов из 3x-ui
    await remove_subscriptions_from_3xui()

    # 2. Очищаем БД
    await clear_database()

    print("\nГотово.")


if __name__ == "__main__":
    asyncio.run(main())

