"""Сценарий: формирование отчёта руководителем центра.

Журнал первичен: статусы «утерян» и «повторно обнаружен» за период берутся
из журнала событий, а не из текущего состояния каталога.
"""
from datetime import datetime
from statistics import mean
from typing import Callable

from model.access import AccessPolicy, Action
from model.dto import Metric, ReportData, UserDto
from model.entities import ObservationTool
from model.enums import EventType, ObjectType, ToolStatus
from model.exceptions import ValidationError
from model.repositories import (JournalRepository, SessionRepository, SpaceObjectRepository,
                                ToolRepository)
from model.settings import (SPACE_MAX_ALTITUDE_KM, SPACE_MAX_INCLINATION_DEG,
                            SPACE_MIN_ALTITUDE_KM, SPACE_MIN_INCLINATION_DEG)


def _union_area(rects: list[tuple[float, float, float, float]]) -> float:
    """Площадь объединения прямоугольников (x1, x2, y1, y2)."""
    xs = sorted({x for r in rects for x in (r[0], r[1])})
    total = 0.0
    for left, right in zip(xs, xs[1:]):
        spans = sorted((r[2], r[3]) for r in rects if r[0] <= left and r[1] >= right)
        covered, current_end = 0.0, None
        for start, end in spans:
            if current_end is None or start > current_end:
                covered += end - start
                current_end = end
            elif end > current_end:
                covered += end - current_end
                current_end = end
        total += covered * (right - left)
    return total


class ReportService:
    def __init__(self, objects: SpaceObjectRepository, tools: ToolRepository,
                 sessions: SessionRepository, journal: JournalRepository,
                 policy: AccessPolicy, clock: Callable[[], datetime]) -> None:
        self._objects = objects
        self._tools = tools
        self._sessions = sessions
        self._journal = journal
        self._policy = policy
        self._clock = clock

    def build_report(self, user: UserDto, period_from: datetime,
                     period_to: datetime) -> ReportData:
        """Сценарий 4. Сформировать отчёт за период (только руководитель центра)."""
        self._policy.check(user.role, Action.BUILD_REPORT)
        if period_from > period_to:
            raise ValidationError("Начало периода не может быть позже конца")

        objects = [o for o in self._objects.get_all() if o.registered_at <= period_to]
        return ReportData(
            period_from=period_from,
            period_to=period_to,
            counts_by_type=self._counts_by_type(objects),
            dangerous_approaches=None,   # расчёт сближений не входит в реализованное ядро
            lost_share=self._lost_share(len(objects), period_to),
            rediscovered_share=self._rediscovered_share(period_from, period_to),
            orbit_coverage=self._orbit_coverage(self._tools.get_all()),
            avg_gap_hours=self._avg_gap_hours(period_from, period_to),
        )

    @staticmethod
    def _counts_by_type(objects) -> dict[str, int] | None:
        if not objects:
            return None
        counts = {t.label: 0 for t in ObjectType}
        for o in objects:
            counts[o.object_type.label] += 1
        return counts

    def _lost_share(self, total_objects: int, period_to: datetime) -> Metric:
        """Доля объектов, которые на конец периода числятся утерянными (по журналу)."""
        if total_objects == 0:
            return Metric(None)
        last_event: dict[str, EventType] = {}
        for entry in self._journal.until(period_to):
            if entry.event_type in (EventType.LOST, EventType.REDISCOVERED):
                last_event[entry.catalog_number] = entry.event_type
        lost = sum(1 for e in last_event.values() if e is EventType.LOST)
        return Metric(lost / total_objects, lost, total_objects)

    def _rediscovered_share(self, period_from: datetime, period_to: datetime) -> Metric:
        """Повторно обнаруженные за период / объекты, утерянные хотя бы раз к концу периода."""
        entries = self._journal.until(period_to)
        ever_lost = {e.catalog_number for e in entries if e.event_type is EventType.LOST}
        rediscovered = {e.catalog_number for e in entries
                        if e.event_type is EventType.REDISCOVERED
                        and period_from <= e.occurred_at <= period_to}
        if not ever_lost:
            return Metric(None)
        return Metric(len(rediscovered) / len(ever_lost), len(rediscovered), len(ever_lost))

    @staticmethod
    def _orbit_coverage(tools: list[ObservationTool]) -> Metric:
        """Доля орбитального пространства (высота × наклонение), покрытая средствами в строю."""
        if not tools:
            return Metric(None)
        rects = []
        for t in tools:
            if t.status is not ToolStatus.IN_SERVICE:
                continue
            z = t.zone
            rect = (max(z.min_altitude_km, SPACE_MIN_ALTITUDE_KM),
                    min(z.max_altitude_km, SPACE_MAX_ALTITUDE_KM),
                    max(z.min_inclination_deg, SPACE_MIN_INCLINATION_DEG),
                    min(z.max_inclination_deg, SPACE_MAX_INCLINATION_DEG))
            if rect[0] < rect[1] and rect[2] < rect[3]:
                rects.append(rect)
        total = ((SPACE_MAX_ALTITUDE_KM - SPACE_MIN_ALTITUDE_KM)
                 * (SPACE_MAX_INCLINATION_DEG - SPACE_MIN_INCLINATION_DEG))
        return Metric(_union_area(rects) / total if rects else 0.0)

    def _avg_gap_hours(self, period_from: datetime, period_to: datetime) -> Metric:
        """Для каждого объекта — среднее время между соседними наблюдениями периода,
        затем среднее по объектам. Объекты с менее чем двумя наблюдениями не учитываются."""
        by_object: dict[str, list[datetime]] = {}
        for s in self._sessions.between(period_from, period_to):
            by_object.setdefault(s.catalog_number, []).append(s.observed_at)
        per_object = []
        for times in by_object.values():
            if len(times) >= 2:
                times.sort()
                gaps = [(b - a).total_seconds() / 3600 for a, b in zip(times, times[1:])]
                per_object.append(mean(gaps))
        if not per_object:
            return Metric(None)
        return Metric(mean(per_object), None, len(per_object))
