"""Сценарий: проведение наблюдения (с проверкой зоны, чувствительности, режима)."""
from datetime import datetime
from typing import Callable

from model.access import AccessPolicy, Action
from model.dto import SessionDto, ToolDto, UserDto
from model.entities import JournalEntry, ObservationSession
from model.enums import EventType, UserRole
from model.events import EventBus, ModelEvent
from model.exceptions import ValidationError
from model.repositories import (JournalRepository, SessionRepository, SpaceObjectRepository,
                                ToolRepository)


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
                         observed_at: datetime | None, raw_data: str) -> SessionDto:
        """Сценарий 2. Провести наблюдение.

        Если объект был «утерян», он получает статус «повторно обнаружен»
        и сохраняет прежний каталожный номер.
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
        obj = self._objects.get(catalog_number.strip())
        if obj is None:
            raise ValidationError(f"Объект с номером «{catalog_number}» не найден в каталоге")
        if when < obj.registered_at:
            raise ValidationError("Наблюдение не может быть раньше регистрации объекта")

        tool.ensure_can_observe(obj)

        rediscovered = obj.register_observation(when)
        result = ("Повторное обнаружение: статус «утерян» снят" if rediscovered
                  else "Наблюдение принято")
        session = self._sessions.add(ObservationSession(
            None, tool.tool_id, obj.catalog_number, when, raw_data.strip(), result, user.login))
        self._objects.update(obj)
        if rediscovered:
            self._journal.add(JournalEntry(
                None, EventType.REDISCOVERED, obj.catalog_number, when,
                f"Обнаружен средством {tool.tool_id}"))
        self._bus.publish(ModelEvent("observation_added", obj.catalog_number))
        return SessionDto.from_entity(session, rediscovered)
