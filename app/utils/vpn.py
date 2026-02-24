"""
Утилиты для генерации VPN ссылок и работы с подписками.
"""
import json
import urllib.parse
from typing import Dict, Any


def generate_vless_link(
    uuid: str,
    base_host: str,
    port: int,
    email: str,
    stream_settings_str: str
) -> str:
    """
    Генерация VLESS Reality ссылки.
    
    Args:
        uuid: UUID клиента
        base_host: Хост сервера
        port: Порт подключения
        email: Email клиента (идентификатор)
        stream_settings_str: JSON настройки stream
    
    Returns:
        VLESS ссылка для подключения
    """
    stream_settings = json.loads(stream_settings_str or '{}')
    reality_settings = stream_settings.get('realitySettings', {})
    pbk = reality_settings.get('settings', {}).get('publicKey', '')
    sid = reality_settings.get('shortIds', [''])[0]
    fp = reality_settings.get('settings', {}).get('fingerprint', 'random')
    spx = reality_settings.get('settings', {}).get('spiderX', '/')
    sni = reality_settings.get('serverNames', [''])[0]

    name_encoded = urllib.parse.quote(f"🇩🇪 reality-{email}")

    return (
        f"vless://{uuid}@{base_host}:{port}?"
        f"type=tcp&encryption=none&security=reality&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx={spx}&flow=xtls-rprx-vision"
        f"#{name_encoded}"
    )


def get_subscription_link(base_host: str, email: str) -> str:
    """
    Генерация ссылки на подписку.
    
    Args:
        base_host: Хост сервера
        email: Email клиента
    
    Returns:
        URL ссылки на подписку
    """
    return f"https://{base_host}/egcPsGWuDm/{email}"


def extract_base_host(api_url: str) -> str:
    """
    Извлечение базового хоста из API URL.
    
    Args:
        api_url: Полный URL API (например, http://1.2.3.4:2053)
    
    Returns:
        Базовый хост без протокола и порта
    """
    return api_url.split('//')[1].split('/')[0].split(':')[0]


def get_port_from_stream(stream_settings_str: str, default_port: int = 443) -> int:
    """
    Получение порта из настроек stream.
    
    Args:
        stream_settings_str: JSON настройки stream
        default_port: Порт по умолчанию
    
    Returns:
        Номер порта
    """
    if not stream_settings_str:
        return default_port
        
    stream_settings = json.loads(stream_settings_str)
    external_proxies = stream_settings.get('externalProxy', [])
    
    if external_proxies:
        return external_proxies[0].get('port', default_port)
    
    return default_port
