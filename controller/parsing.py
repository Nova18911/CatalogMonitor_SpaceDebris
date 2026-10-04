"""Преобразование введённых строк в числа и даты. Ошибка -> ValueError с понятным текстом."""
from datetime import datetime, timedelta


def parse_float(text: str, field: str) -> float:
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"поле «{field}» должно быть числом") from None


def parse_datetime(text: str, field: str) -> datetime | None:
    """Пустая строка -> None (значит «сейчас»)."""
    text = text.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"поле «{field}» должно иметь вид ГГГГ-ММ-ДД ЧЧ:ММ")


def parse_day_start(text: str, field: str) -> datetime:
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"поле «{field}» должно иметь вид ГГГГ-ММ-ДД") from None


def parse_day_end(text: str, field: str) -> datetime:
    return parse_day_start(text, field) + timedelta(days=1) - timedelta(seconds=1)
