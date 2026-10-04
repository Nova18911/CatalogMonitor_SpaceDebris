"""Сценарии: регистрация объекта в каталоге и присвоение статуса «утерян»."""
import re
from datetime import datetime, timedelta
from typing import Callable

from model.access import AccessPolicy, Action
from model.dto import SpaceObjectDto, UserDto
from model.entities import JournalEntry, OrbitalElements, SpaceObject
from model.enums import EventType, ObjectStatus, ObjectType
from model.events import EventBus, ModelEvent
from model.exceptions import ValidationError
from model.repositories import JournalRepository, SpaceObjectRepository
from model.settings import LOST_AFTER_DAYS

# Международное обозначение: год, номер запуска, часть запуска (например 1998-067A).
DESIGNATOR_PATTERN = re.compile(r"^\d{4}-\d{3}[A-Z]{1,3}$")


class CatalogService:
    def __init__(self, objects: SpaceObjectRepository, journal: JournalRepository,
                 policy: AccessPolicy, bus: EventBus, clock: Callable[[], datetime],
                 lost_after: timedelta = timedelta(days=LOST_AFTER_DAYS)) -> None:
        self._objects = objects
        self._journal = journal
        self._policy = policy
        self._bus = bus
        self._clock = clock
        self._lost_after = lost_after

    def list_objects(self, user: UserDto) -> list[SpaceObjectDto]:
        self._policy.check(user.role, Action.VIEW_CATALOG)
        return [SpaceObjectDto.from_entity(o) for o in self._objects.get_all()]

    def register_object(self, user: UserDto, intl_designator: str, object_type: ObjectType,
                        size_m: float, elements: OrbitalElements) -> SpaceObjectDto:
        """Сценарий 1. Зарегистрировать объект: проверить данные, присвоить каталожный номер."""
        self._policy.check(user.role, Action.REGISTER_OBJECT)
        designator = intl_designator.strip().upper()
        if not designator:
            raise ValidationError("Международный идентификатор обязателен")
        if not DESIGNATOR_PATTERN.match(designator):
            raise ValidationError(
                "Международный идентификатор должен иметь вид 1998-067A "
                "(год, номер запуска, буквы)")
        if size_m <= 0:
            raise ValidationError("Размерная оценка должна быть больше нуля")
        elements.validate()
        if self._objects.designator_exists(designator):
            raise ValidationError(
                f"Объект с идентификатором {designator} уже есть в каталоге")

        now = self._clock()
        number = self._objects.next_catalog_number()
        obj = SpaceObject(number, designator, object_type, size_m, elements,
                          ObjectStatus.CATALOGED, registered_at=now)
        self._objects.add(obj)
        self._journal.add(JournalEntry(None, EventType.REGISTERED, number, now,
                                       f"Регистрация объекта {designator}"))
        self._bus.publish(ModelEvent("object_registered", number))
        return SpaceObjectDto.from_entity(obj)

    def check_lost(self, user: UserDto) -> list[SpaceObjectDto]:
        """Сценарий 3. Присвоить статус «утерян» объектам, не наблюдавшимся дольше срока."""
        self._policy.check(user.role, Action.CHECK_LOST)
        now = self._clock()
        newly_lost: list[SpaceObjectDto] = []
        for obj in self._objects.get_all():
            if obj.status is ObjectStatus.LOST or not obj.is_overdue(now, self._lost_after):
                continue
            obj.mark_lost(now, self._lost_after)
            self._objects.update(obj)
            self._journal.add(JournalEntry(
                None, EventType.LOST, obj.catalog_number, now,
                f"Нет наблюдений более {self._lost_after.days} сут."))
            newly_lost.append(SpaceObjectDto.from_entity(obj))
        if newly_lost:
            self._bus.publish(ModelEvent("objects_lost", [o.catalog_number for o in newly_lost]))
        return newly_lost
