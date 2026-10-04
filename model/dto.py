"""Данные для показа: неизменяемые объекты, которые Модель отдаёт наружу.

View и Controller получают их вместо изменяемых сущностей и не могут нарушить
правила предметной области.
"""
from dataclasses import dataclass
from datetime import datetime

from model.entities import ObservationSession, ObservationTool, SpaceObject
from model.enums import UserRole

DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def format_dt(value: datetime | None) -> str:
    return value.strftime(DATETIME_FORMAT) if value else "—"


@dataclass(frozen=True)
class UserDto:
    login: str
    full_name: str
    role: UserRole


@dataclass(frozen=True)
class SpaceObjectDto:
    catalog_number: str
    intl_designator: str
    type_label: str
    size_m: float
    altitude_km: float
    inclination_deg: float
    status_label: str
    last_observed: str

    @classmethod
    def from_entity(cls, o: SpaceObject) -> "SpaceObjectDto":
        return cls(o.catalog_number, o.intl_designator, o.object_type.label, o.size_m,
                   round(o.elements.altitude_km), o.elements.inclination_deg,
                   o.status.label, format_dt(o.last_observed_at))


@dataclass(frozen=True)
class ToolDto:
    tool_id: str
    description: str
    in_service: bool

    @classmethod
    def from_entity(cls, t: ObservationTool) -> "ToolDto":
        text = f"{t.tool_id} — {t.tool_type.label}, {t.mode.label} ({t.status.label})"
        return cls(t.tool_id, text, t.status.name == "IN_SERVICE")


@dataclass(frozen=True)
class SessionDto:
    session_id: int
    observed_at: str
    tool_id: str
    catalog_number: str
    operator: str
    result: str
    rediscovered: bool = False

    @classmethod
    def from_entity(cls, s: ObservationSession, rediscovered: bool = False) -> "SessionDto":
        return cls(s.session_id, format_dt(s.observed_at), s.tool_id, s.catalog_number,
                   s.operator_login, s.result, rediscovered)


@dataclass(frozen=True)
class Metric:
    """Показатель отчёта. ``value is None`` означает «нет данных» (это не ноль)."""
    value: float | None
    numerator: int | None = None
    denominator: int | None = None


@dataclass(frozen=True)
class ReportData:
    period_from: datetime
    period_to: datetime
    counts_by_type: dict[str, int] | None   # None -> нет данных
    dangerous_approaches: int | None        # None -> нет данных
    lost_share: Metric                      # 0..1
    rediscovered_share: Metric              # 0..1
    orbit_coverage: Metric                  # 0..1
    avg_gap_hours: Metric                   # часы
