"""Сущности предметной области и правила, которые к ним относятся."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from model.enums import (ObjectStatus, ObjectType, OperatingMode, ToolStatus,
                         ToolType, UserRole, EventType)
from model.exceptions import InvalidTransitionError, ValidationError
from model.settings import EARTH_RADIUS_KM


@dataclass
class OrbitalElements:
    """Орбитальные элементы (упрощённый набор)."""
    semi_major_axis_km: float
    eccentricity: float
    inclination_deg: float

    @property
    def altitude_km(self) -> float:
        """Примерная высота орбиты над поверхностью Земли."""
        return self.semi_major_axis_km - EARTH_RADIUS_KM

    def validate(self) -> None:
        if self.semi_major_axis_km <= EARTH_RADIUS_KM:
            raise ValidationError(
                f"Большая полуось должна быть больше радиуса Земли ({EARTH_RADIUS_KM:.0f} км)")
        if not 0 <= self.eccentricity < 1:
            raise ValidationError("Эксцентриситет должен быть в диапазоне от 0 до 1")
        if not 0 <= self.inclination_deg <= 180:
            raise ValidationError("Наклонение должно быть в диапазоне от 0 до 180°")


@dataclass
class SpaceObject:
    """Космический объект каталога."""
    catalog_number: str
    intl_designator: str
    object_type: ObjectType
    size_m: float
    elements: OrbitalElements
    status: ObjectStatus
    registered_at: datetime
    last_observed_at: datetime | None = None

    def is_overdue(self, now: datetime, max_gap: timedelta) -> bool:
        """Превышен ли срок отсутствия наблюдений."""
        reference = self.last_observed_at or self.registered_at
        return now - reference > max_gap

    def mark_lost(self, now: datetime, max_gap: timedelta) -> None:
        """Присвоить статус «утерян» (только если срок действительно превышен)."""
        if self.status is ObjectStatus.LOST:
            raise InvalidTransitionError(
                f"Объект {self.catalog_number} уже имеет статус «утерян»")
        if not self.is_overdue(now, max_gap):
            raise InvalidTransitionError(
                f"Срок отсутствия наблюдений объекта {self.catalog_number} не превышен")
        self.status = ObjectStatus.LOST

    def register_observation(self, when: datetime) -> bool:
        """Учесть наблюдение. Возвращает True, если это повторное обнаружение.

        Переходы: утерян -> повторно обнаружен; повторно обнаружен -> каталогизирован.
        Каталожный номер при этом не меняется.
        """
        rediscovered = self.status is ObjectStatus.LOST
        if rediscovered:
            self.status = ObjectStatus.REDISCOVERED
        elif self.status is ObjectStatus.REDISCOVERED:
            self.status = ObjectStatus.CATALOGED
        if self.last_observed_at is None or when > self.last_observed_at:
            self.last_observed_at = when
        return rediscovered


@dataclass
class CoverageZone:
    """Зона обзора средства: диапазоны высот и наклонений."""
    min_altitude_km: float
    max_altitude_km: float
    min_inclination_deg: float
    max_inclination_deg: float

    def contains(self, elements: OrbitalElements) -> bool:
        return (self.min_altitude_km <= elements.altitude_km <= self.max_altitude_km
                and self.min_inclination_deg <= elements.inclination_deg <= self.max_inclination_deg)


@dataclass
class ObservationTool:
    """Средство наблюдения."""
    tool_id: str
    tool_type: ToolType
    zone: CoverageZone
    sensitivity_m: float  # минимальный размер объекта, который средство способно обнаружить
    mode: OperatingMode
    status: ToolStatus

    def ensure_can_observe(self, obj: SpaceObject) -> None:
        """Проверить, может ли средство наблюдать объект; иначе ValidationError."""
        if self.status is not ToolStatus.IN_SERVICE:
            raise ValidationError(
                f"Средство {self.tool_id} недоступно: статус «{self.status.label}»")
        if not self.mode.supports(obj.object_type):
            raise ValidationError(
                f"Режим работы «{self.mode.label}» несовместим с типом объекта "
                f"«{obj.object_type.label}»")
        if not self.zone.contains(obj.elements):
            raise ValidationError(
                f"Объект вне зоны обзора средства {self.tool_id} "
                f"(высота {obj.elements.altitude_km:.0f} км, "
                f"наклонение {obj.elements.inclination_deg:.1f}°)")
        if obj.size_m < self.sensitivity_m:
            raise ValidationError(
                f"Размер объекта ({obj.size_m} м) ниже чувствительности "
                f"средства {self.tool_id} ({self.sensitivity_m} м)")


@dataclass
class ObservationSession:
    """Сеанс наблюдения: одно средство наблюдает один объект."""
    session_id: int | None
    tool_id: str
    catalog_number: str
    observed_at: datetime
    raw_data: str
    result: str
    operator_login: str


@dataclass
class JournalEntry:
    """Запись журнала (не изменяется после создания)."""
    entry_id: int | None
    event_type: EventType
    catalog_number: str
    occurred_at: datetime
    details: str


@dataclass
class User:
    login: str
    password_hash: str
    full_name: str
    role: UserRole
