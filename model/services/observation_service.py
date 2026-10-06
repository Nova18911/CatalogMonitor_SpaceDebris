"""Сценарий: проведение наблюдения (с проверкой зоны, чувствительности, режима)."""
from datetime import datetime
from typing import Callable

from model.access import AccessPolicy, Action
from model.dto import SessionDto, ToolDto, UserDto
from model.entities import JournalEntry, ObservationSession, OrbitalElements, SpaceObject
from model.enums import EventType, ObjectStatus, ObjectType, UserRole
from model.events import EventBus, ModelEvent
from model.exceptions import ValidationError
from model.repositories import (JournalRepository, SessionRepository, SpaceObjectRepository,
                                ToolRepository)
from model.settings import CONFIRM_TIMEOUT_HOURS
from datetime import timedelta

class ObservationService:
    def __init__(self, objects: SpaceObjectRepository, tools: ToolRepository,
                 sessions: SessionRepository, journal: JournalRepository,
                 policy: AccessPolicy, bus: EventBus, clock: Callable[[], datetime]) -> None:
        self._objects = objects
        self._tools = tools
        self._sessions = sessions
        self._journal = journal
        self._policy = policy
        self._bus = bus
        self._clock = clock

    def list_tools(self, user: UserDto) -> list[ToolDto]:
        self._policy.check(user.role, Action.ADD_OBSERVATION)
        return [ToolDto.from_entity(t) for t in self._tools.get_all()]

    def list_sessions(self, user: UserDto, limit: int = 30) -> list[SessionDto]:
        """Оператор видит только свои сеансы."""
        self._policy.check(user.role, Action.ADD_OBSERVATION)
        own_only = user.login if user.role is UserRole.OBSERVER_OPERATOR else None
        return [SessionDto.from_entity(s) for s in self._sessions.recent(limit, own_only)]

    def register_session(self, user: UserDto, tool_id: str, catalog_number: str,
                         observed_at: datetime | None, raw_data: str,
                         # --- новые необязательные параметры для нового объекта ---
                         intl_designator: str | None = None,
                         object_type: ObjectType | None = None,
                         size_m: float | None = None,
                         elements: OrbitalElements | None = None) -> SessionDto:
        """Сценарий 2. Провести наблюдение.

        Если объект найден — обычная логика (в т.ч. повторное обнаружение).
        Если объект НЕ найден и переданы предварительные данные —
        создаётся запись со статусом «подтверждается».
        Если объект НЕ найден и данные не переданы — ValidationError
        (существующие сценарии не ломаются).
        """
        self._policy.check(user.role, Action.ADD_OBSERVATION)
        now = self._clock()
        when = observed_at or now
        if not raw_data.strip():
            raise ValidationError("Полученные данные наблюдения обязательны")
        if when > now:
            raise ValidationError("Время наблюдения не может быть в будущем")

        tool = self._tools.get(tool_id)
        if tool is None:
            raise ValidationError("Выберите средство наблюдения")

        catalog_number = catalog_number.strip()
        obj = self._objects.get(catalog_number)

        if obj is None:
            # --- новый объект: создаём со статусом «подтверждается» ---
            if not all([intl_designator, object_type is not None, size_m is not None, elements]):
                raise ValidationError(
                    f"Объект с номером «{catalog_number}» не найден в каталоге. "
                    "Для создания предварительной записи передайте "
                    "международный идентификатор, тип, размер и орбитальные элементы.")
            if size_m <= 0:
                raise ValidationError("Размерная оценка должна быть больше нуля")
            elements.validate()
            from model.services.catalog_service import normalize_designator, DESIGNATOR_PATTERN
            designator = normalize_designator(intl_designator)
            if not DESIGNATOR_PATTERN.match(designator):
                raise ValidationError(
                    "Международный идентификатор должен иметь вид 1998-067A")
            if self._objects.designator_exists(designator):
                raise ValidationError(
                    f"Объект с идентификатором {designator} уже есть в каталоге")

            # предварительный каталожный номер (можно оставить переданный или сгенерировать)
            number = catalog_number or self._objects.next_catalog_number()
            if self._objects.get(number):
                number = self._objects.next_catalog_number()

            obj = SpaceObject(
                number, designator, object_type, size_m, elements,
                ObjectStatus.CONFIRMING, registered_at=when, last_observed_at=when)
            tool.ensure_can_observe(obj)  # зона / чувствительность / режим
            self._objects.add(obj)
            self._journal.add(JournalEntry(
                None, EventType.CONFIRMING_CREATED, number, when,
                f"Предварительная запись по наблюдению средством {tool.tool_id}, "
                f"оператор {user.login}"))
            result = "Создан объект со статусом «подтверждается»"
            session = self._sessions.add(ObservationSession(
                None, tool.tool_id, obj.catalog_number, when,
                raw_data.strip(), result, user.login))
            self._bus.publish(ModelEvent("observation_added", obj.catalog_number))
            return SessionDto.from_entity(session, rediscovered=False)

        # --- существующий объект ---
        if when < obj.registered_at:
            raise ValidationError("Наблюдение не может быть раньше регистрации объекта")
        tool.ensure_can_observe(obj)

        was_confirming = obj.status is ObjectStatus.CONFIRMING
        rediscovered = obj.register_observation(when)
        if was_confirming and obj.status is ObjectStatus.CATALOGED:
            result = "Объект подтверждён: статус «каталогизирован»"
            self._journal.add(JournalEntry(
                None, EventType.CONFIRMED, obj.catalog_number, when,
                f"Подтверждён повторным наблюдением средством {tool.tool_id}"))
        else:
            result = ("Повторное обнаружение: статус «утерян» снят" if rediscovered
                      else "Наблюдение принято")
            if rediscovered:
                self._journal.add(JournalEntry(
                    None, EventType.REDISCOVERED, obj.catalog_number, when,
                    f"Обнаружен средством {tool.tool_id}"))

        session = self._sessions.add(ObservationSession(
            None, tool.tool_id, obj.catalog_number, when,
            raw_data.strip(), result, user.login))
        self._objects.update(obj)
        self._bus.publish(ModelEvent("observation_added", obj.catalog_number))
        return SessionDto.from_entity(session, rediscovered)

    def cleanup_unconfirmed(self, user: UserDto) -> list[str]:
        """Удалить объекты со статусом «подтверждается», которые не подтверждены
        в течение CONFIRM_TIMEOUT_HOURS. Возвращает список удалённых каталожных номеров.
        """
        self._policy.check(user.role, Action.CHECK_LOST)  # или ввести отдельное Action
        now = self._clock()
        timeout = timedelta(hours=CONFIRM_TIMEOUT_HOURS)
        deleted: list[str] = []
        for obj in list(self._objects.get_all()):
            if obj.status is not ObjectStatus.CONFIRMING:
                continue
            reference = obj.last_observed_at or obj.registered_at
            if now - reference <= timeout:
                continue
            self._objects.delete(obj.catalog_number)
            self._journal.add(JournalEntry(
                None, EventType.UNCONFIRMED_DELETED, obj.catalog_number, now,
                f"Не подтверждён в течение {CONFIRM_TIMEOUT_HOURS} ч, удалён автоматически"))
            deleted.append(obj.catalog_number)
        if deleted:
            self._bus.publish(ModelEvent("objects_deleted", deleted))
        return deleted