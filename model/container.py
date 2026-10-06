"""Сборка Модели: репозитории, сервисы и шина событий в одном месте."""
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from model.access import AccessPolicy
from model.database import Database
from model.events import EventBus
from model.repositories import (JournalRepository, SessionRepository, SpaceObjectRepository,
                                ToolRepository, UserRepository)
from model.services.auth_service import AuthService
from model.services.catalog_service import CatalogService
from model.services.observation_service import ObservationService
from model.services.report_service import ReportService


def system_clock() -> datetime:
    return datetime.now().replace(microsecond=0)


@dataclass
class ModelContainer:
    """Всё, что Контроллер получает от Модели."""
    bus: EventBus
    auth: AuthService
    catalog: CatalogService
    observation: ObservationService
    report: ReportService
    users: UserRepository
    objects: SpaceObjectRepository
    tools: ToolRepository
    sessions: SessionRepository
    journal: JournalRepository
    _db: Database | None = None

    def close(self) -> None:
        """Закрыть соединение с БД (оптимизация утечки дескрипторов)."""
        if self._db is not None:
            self._db.close()
            self._db = None


def build_model(db_path: str = ":memory:",
                clock: Callable[[], datetime] = system_clock) -> ModelContainer:
    db = Database(db_path)
    users, objects, tools = UserRepository(db), SpaceObjectRepository(db), ToolRepository(db)
    sessions, journal = SessionRepository(db), JournalRepository(db)
    policy, bus = AccessPolicy(), EventBus()
    return ModelContainer(
        bus=bus,
        auth=AuthService(users, policy),
        catalog=CatalogService(objects, journal, policy, bus, clock),
        observation=ObservationService(objects, tools, sessions, journal, policy, bus, clock),
        report=ReportService(objects, tools, sessions, journal, policy, clock),
        users=users, objects=objects, tools=tools, sessions=sessions, journal=journal,
        _db=db,
    )