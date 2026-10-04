"""Перечисления предметной области.

В базе хранится имя элемента (``ObjectType.FRAGMENT``), на экране показывается
русская подпись (``label``).
"""
from enum import Enum


class LabeledEnum(Enum):
    """Перечисление с русской подписью и поиском по подписи."""

    @property
    def label(self) -> str:
        return self.value

    @classmethod
    def from_label(cls, label: str):
        for member in cls:
            if member.value == label:
                return member
        raise ValueError(f"неизвестное значение «{label}»")


class ObjectType(LabeledEnum):
    ACTIVE_SATELLITE = "Действующий спутник"
    DECOMMISSIONED = "Выведенный из эксплуатации аппарат"
    FRAGMENT = "Фрагмент"
    ROCKET_STAGE = "Ступень ракеты"


class ObjectStatus(LabeledEnum):
    CATALOGED = "Каталогизирован"
    LOST = "Утерян"
    REDISCOVERED = "Повторно обнаружен"


class ToolType(LabeledEnum):
    RADAR = "Радиолокатор"
    OPTICAL_TELESCOPE = "Оптический телескоп"
    LASER_RANGEFINDER = "Лазерный дальномер"


class ToolStatus(LabeledEnum):
    IN_SERVICE = "В строю"
    MAINTENANCE = "На обслуживании"
    FAILED = "Вышло из строя"


class OperatingMode(LabeledEnum):
    SURVEY = "Обзор"
    TRACKING = "Сопровождение"
    DEBRIS_SEARCH = "Поиск фрагментов"

    def supports(self, object_type: ObjectType) -> bool:
        """Совместим ли режим работы с типом объекта."""
        return object_type in _MODE_TYPES[self]


# Какие типы объектов можно наблюдать в каждом режиме.
_MODE_TYPES = {
    OperatingMode.SURVEY: set(ObjectType),
    OperatingMode.TRACKING: {ObjectType.ACTIVE_SATELLITE, ObjectType.DECOMMISSIONED},
    OperatingMode.DEBRIS_SEARCH: {ObjectType.FRAGMENT, ObjectType.ROCKET_STAGE},
}


class UserRole(LabeledEnum):
    OBSERVER_OPERATOR = "Оператор наблюдения"
    ORBIT_ANALYST = "Аналитик орбитального движения"
    NOTIFICATION_SPECIALIST = "Специалист по уведомлениям"
    MAINTENANCE_ENGINEER = "Инженер по обслуживанию средств"
    SATELLITE_OWNER = "Владелец спутника"
    CENTER_HEAD = "Руководитель центра"
    ADMIN = "Администратор системы"


class EventType(LabeledEnum):
    """Типы записей журнала (журнал первичен для отчёта)."""
    REGISTERED = "Регистрация объекта"
    LOST = "Присвоен статус «утерян»"
    REDISCOVERED = "Повторное обнаружение"
