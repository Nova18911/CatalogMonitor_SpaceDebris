"""Хранилища. Сервисы зависят от интерфейса ``IRepository``, а не от SQLite."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar

from model.database import Database
from model.entities import (CoverageZone, JournalEntry, ObservationSession, ObservationTool,
                            OrbitalElements, SpaceObject, User)
from model.enums import (EventType, ObjectStatus, ObjectType, OperatingMode, ToolStatus,
                         ToolType, UserRole)

T = TypeVar("T")


def _to_text(value: datetime | None) -> str | None:
    return value.isoformat(sep=" ", timespec="seconds") if value else None


def _from_text(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class IRepository(ABC, Generic[T]):
    """Единый интерфейс хранилища."""

    @abstractmethod
    def add(self, item: T) -> T: ...

    @abstractmethod
    def get(self, key) -> T | None: ...

    @abstractmethod
    def get_all(self) -> list[T]: ...

    @abstractmethod
    def update(self, item: T) -> None: ...


class UserRepository(IRepository[User]):
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, item: User) -> User:
        self._db.execute("INSERT INTO users VALUES (?,?,?,?)",
                         (item.login, item.password_hash, item.full_name, item.role.name))
        return item

    def get(self, key: str) -> User | None:
        rows = self._db.query("SELECT * FROM users WHERE login=?", (key,))
        return self._build(rows[0]) if rows else None

    def get_all(self) -> list[User]:
        return [self._build(r) for r in self._db.query("SELECT * FROM users")]

    def update(self, item: User) -> None:
        raise NotImplementedError("Правка пользователей не входит в реализованное ядро")

    @staticmethod
    def _build(r) -> User:
        return User(r["login"], r["password_hash"], r["full_name"], UserRole[r["role"]])


class SpaceObjectRepository(IRepository[SpaceObject]):
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, item: SpaceObject) -> SpaceObject:
        e = item.elements
        self._db.execute(
            "INSERT INTO space_objects VALUES (?,?,?,?,?,?,?,?,?,?)",
            (item.catalog_number, item.intl_designator, item.object_type.name, item.size_m,
             e.semi_major_axis_km, e.eccentricity, e.inclination_deg, item.status.name,
             _to_text(item.registered_at), _to_text(item.last_observed_at)))
        return item

    def get(self, key: str) -> SpaceObject | None:
        rows = self._db.query("SELECT * FROM space_objects WHERE catalog_number=?", (key,))
        return self._build(rows[0]) if rows else None

    def get_all(self) -> list[SpaceObject]:
        rows = self._db.query("SELECT * FROM space_objects ORDER BY catalog_number")
        return [self._build(r) for r in rows]

    def update(self, item: SpaceObject) -> None:
        e = item.elements
        self._db.execute(
            "UPDATE space_objects SET object_type=?, size_m=?, semi_major_axis_km=?, "
            "eccentricity=?, inclination_deg=?, status=?, last_observed_at=? "
            "WHERE catalog_number=?",
            (item.object_type.name, item.size_m, e.semi_major_axis_km, e.eccentricity,
             e.inclination_deg, item.status.name, _to_text(item.last_observed_at),
             item.catalog_number))

    def designator_exists(self, designator: str) -> bool:
        return bool(self._db.query(
            "SELECT 1 FROM space_objects WHERE intl_designator=?", (designator,)))

    def next_catalog_number(self) -> str:
        row = self._db.query(
            "SELECT MAX(CAST(catalog_number AS INTEGER)) AS m FROM space_objects")[0]
        return f"{(row['m'] or 0) + 1:05d}"

    @staticmethod
    def _build(r) -> SpaceObject:
        return SpaceObject(
            r["catalog_number"], r["intl_designator"], ObjectType[r["object_type"]],
            r["size_m"],
            OrbitalElements(r["semi_major_axis_km"], r["eccentricity"], r["inclination_deg"]),
            ObjectStatus[r["status"]], _from_text(r["registered_at"]),
            _from_text(r["last_observed_at"]))


class ToolRepository(IRepository[ObservationTool]):
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, item: ObservationTool) -> ObservationTool:
        z = item.zone
        self._db.execute(
            "INSERT INTO tools VALUES (?,?,?,?,?,?,?,?,?)",
            (item.tool_id, item.tool_type.name, z.min_altitude_km, z.max_altitude_km,
             z.min_inclination_deg, z.max_inclination_deg, item.sensitivity_m,
             item.mode.name, item.status.name))
        return item

    def get(self, key: str) -> ObservationTool | None:
        rows = self._db.query("SELECT * FROM tools WHERE tool_id=?", (key,))
        return self._build(rows[0]) if rows else None

    def get_all(self) -> list[ObservationTool]:
        return [self._build(r) for r in self._db.query("SELECT * FROM tools ORDER BY tool_id")]

    def update(self, item: ObservationTool) -> None:
        self._db.execute("UPDATE tools SET status=? WHERE tool_id=?",
                         (item.status.name, item.tool_id))

    @staticmethod
    def _build(r) -> ObservationTool:
        zone = CoverageZone(r["min_altitude_km"], r["max_altitude_km"],
                            r["min_inclination_deg"], r["max_inclination_deg"])
        return ObservationTool(r["tool_id"], ToolType[r["tool_type"]], zone,
                               r["sensitivity_m"], OperatingMode[r["mode"]],
                               ToolStatus[r["status"]])


class SessionRepository(IRepository[ObservationSession]):
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, item: ObservationSession) -> ObservationSession:
        cursor = self._db.execute(
            "INSERT INTO sessions (tool_id, catalog_number, observed_at, raw_data, result, "
            "operator_login) VALUES (?,?,?,?,?,?)",
            (item.tool_id, item.catalog_number, _to_text(item.observed_at), item.raw_data,
             item.result, item.operator_login))
        item.session_id = cursor.lastrowid
        return item

    def get(self, key: int) -> ObservationSession | None:
        rows = self._db.query("SELECT * FROM sessions WHERE session_id=?", (key,))
        return self._build(rows[0]) if rows else None

    def get_all(self) -> list[ObservationSession]:
        return [self._build(r) for r in
                self._db.query("SELECT * FROM sessions ORDER BY observed_at")]

    def update(self, item: ObservationSession) -> None:
        raise NotImplementedError("Сеансы наблюдения не изменяются")

    def between(self, start: datetime, end: datetime) -> list[ObservationSession]:
        rows = self._db.query(
            "SELECT * FROM sessions WHERE observed_at BETWEEN ? AND ? ORDER BY observed_at",
            (_to_text(start), _to_text(end)))
        return [self._build(r) for r in rows]

    def recent(self, limit: int, operator_login: str | None = None) -> list[ObservationSession]:
        if operator_login:
            rows = self._db.query(
                "SELECT * FROM sessions WHERE operator_login=? "
                "ORDER BY observed_at DESC, session_id DESC LIMIT ?", (operator_login, limit))
        else:
            rows = self._db.query(
                "SELECT * FROM sessions ORDER BY observed_at DESC, session_id DESC LIMIT ?",
                (limit,))
        return [self._build(r) for r in rows]

    @staticmethod
    def _build(r) -> ObservationSession:
        return ObservationSession(r["session_id"], r["tool_id"], r["catalog_number"],
                                  _from_text(r["observed_at"]), r["raw_data"], r["result"],
                                  r["operator_login"])


class JournalRepository(IRepository[JournalEntry]):
    """Журнал событий. Записи только добавляются (журнал первичен)."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, item: JournalEntry) -> JournalEntry:
        cursor = self._db.execute(
            "INSERT INTO journal (event_type, catalog_number, occurred_at, details) "
            "VALUES (?,?,?,?)",
            (item.event_type.name, item.catalog_number, _to_text(item.occurred_at),
             item.details))
        item.entry_id = cursor.lastrowid
        return item

    def get(self, key: int) -> JournalEntry | None:
        rows = self._db.query("SELECT * FROM journal WHERE entry_id=?", (key,))
        return self._build(rows[0]) if rows else None

    def get_all(self) -> list[JournalEntry]:
        return [self._build(r) for r in
                self._db.query("SELECT * FROM journal ORDER BY occurred_at, entry_id")]

    def update(self, item: JournalEntry) -> None:
        raise NotImplementedError("Записи журнала не изменяются")

    def until(self, end: datetime) -> list[JournalEntry]:
        rows = self._db.query(
            "SELECT * FROM journal WHERE occurred_at <= ? ORDER BY occurred_at, entry_id",
            (_to_text(end),))
        return [self._build(r) for r in rows]

    @staticmethod
    def _build(r) -> JournalEntry:
        return JournalEntry(r["entry_id"], EventType[r["event_type"]], r["catalog_number"],
                            _from_text(r["occurred_at"]), r["details"])
