"""
Пакет утилит для VPN бота.
"""
from app.utils.vpn import (
    generate_vless_link,
    get_subscription_link,
    extract_base_host,
    get_port_from_stream,
)
from app.utils.messages import (
    delete_message_safe,
    delete_messages_safe,
    edit_or_delete_safe,
    MessageCleaner,
)

__all__ = [
    # VPN утилиты
    "generate_vless_link",
    "get_subscription_link",
    "extract_base_host",
    "get_port_from_stream",
    # Утилиты сообщений
    "delete_message_safe",
    "delete_messages_safe",
    "edit_or_delete_safe",
    "MessageCleaner",
]
