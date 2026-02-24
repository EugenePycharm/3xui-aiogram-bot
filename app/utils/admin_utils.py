"""
Утилиты для админ-бота.
"""
import uuid
from datetime import datetime
from typing import Optional


def format_datetime(dt: Optional[datetime]) -> str:
    """Форматировать дату в читаемый формат."""
    if not dt:
        return "Не указана"
    return dt.strftime("%d.%m.%Y %H:%M")


def format_traffic_gb(gb: int) -> str:
    """Форматировать трафик в читаемый формат."""
    if gb <= 0:
        return "∞ Безлимит"
    if gb < 1024:
        return f"{gb} ГБ"
    return f"{gb / 1024:.1f} ТБ"


def generate_uuid() -> str:
    """Сгенерировать новый UUID."""
    return str(uuid.uuid4())


def parse_date_input(date_str: str) -> Optional[datetime]:
    """
    Распарсить ввод даты от пользователя.
    Поддерживаемые форматы:
    - DD.MM.YYYY
    - DD.MM.YYYY HH:MM
    - YYYY-MM-DD
    - YYYY-MM-DD HH:MM
    """
    formats = [
        "%d.%m.%Y",
        "%d.%m.%Y %H:%M",
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def parse_traffic_input(traffic_str: str) -> int:
    """
    Распарсить ввод трафика от пользователя.
    Поддерживаемые форматы:
    - 10 (ГБ)
    - 10GB, 10 ГБ
    - 1TB, 1 ТБ
    - 0 или "unlimited" для безлимита
    """
    traffic_str = traffic_str.strip().lower()

    if traffic_str in ("0", "unlimited", "∞", "безлимит"):
        return 0

    # Удаляем суффиксы
    for suffix in ["гб", "gb", "тб", "tb"]:
        traffic_str = traffic_str.replace(suffix, "").strip()

    try:
        value = float(traffic_str)
        # Если значение меньше 1000, считаем что это ГБ
        # Если больше - возможно это уже байты
        if value > 10000:
            # Скорее всего это байты, конвертируем в ГБ
            return int(value / (1024 ** 3))
        return int(value)
    except ValueError:
        return 0
