"""Ошибки предметной области. Модель сообщает о нарушении правил только ими."""


class DomainError(Exception):
    """Базовая ошибка предметной области (текст понятен пользователю)."""


class ValidationError(DomainError):
    """Данные не прошли проверку (обязательные поля, зона обзора, чувствительность...)."""


class AccessDeniedError(DomainError):
    """У роли нет права на действие."""


class InvalidTransitionError(DomainError):
    """Недопустимый переход между статусами."""
