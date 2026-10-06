"""Генерация тестовых данных большого объёма для профилирования.

Создаёт объекты, сеансы наблюдения и записи журнала с реалистичными значениями
в SQLite-файле того же формата, что использует система.

Использование:
    python scripts/generate_load_data.py --objects 1000  --sessions 3000  --db data/perf/load_1k.db
    python scripts/generate_load_data.py --objects 10000 --sessions 30000 --db data/perf/load_10k.db
    python scripts/generate_load_data.py --objects 50000 --sessions 80000 --db data/perf/load_50k.db
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from model.container import build_model
from model.entities import (
    CoverageZone, JournalEntry, ObservationSession, ObservationTool,
    OrbitalElements, SpaceObject, User,
)
from model.enums import (
    EventType, ObjectStatus, ObjectType, OperatingMode, ToolStatus, ToolType, UserRole,
)
from model.services.auth_service import AuthService

random.seed(42)

OBJECT_TYPES = list(ObjectType)
TOOL_SPECS = [
    ("RAD-01", ToolType.RADAR, CoverageZone(200, 2000, 0, 100), 0.1, OperatingMode.SURVEY),
    ("OPT-01", ToolType.OPTICAL_TELESCOPE, CoverageZone(300, 6000, 0, 120), 0.5, OperatingMode.TRACKING),
    ("LAS-01", ToolType.LASER_RANGEFINDER, CoverageZone(300, 1500, 40, 110), 0.3, OperatingMode.DEBRIS_SEARCH),
    ("RAD-02", ToolType.RADAR, CoverageZone(200, 1500, 0, 100), 0.1, OperatingMode.SURVEY),
]


def _designator(i: int) -> str:
    year = 1990 + (i % 36)
    launch = (i % 999) + 1
    letter = chr(ord("A") + (i % 26))
    return f"{year}-{launch:03d}{letter}"


def generate(db_path: str, n_objects: int, n_sessions: int, now: datetime | None = None) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    now = now or datetime.now().replace(microsecond=0)
    model = build_model(db_path)

    # пользователи
    pwd = AuthService.hash_password("1234")
    for login, name, role in [
        ("operator", "Иванов И. И.", UserRole.OBSERVER_OPERATOR),
        ("analyst", "Петрова А. С.", UserRole.ORBIT_ANALYST),
        ("head", "Сидоров П. А.", UserRole.CENTER_HEAD),
        ("admin", "Админов А. А.", UserRole.ADMIN),
    ]:
        model.users.add(User(login, pwd, name, role))

    # средства наблюдения
    for tool_id, ttype, zone, sens, mode in TOOL_SPECS:
        status = ToolStatus.FAILED if tool_id == "RAD-02" else ToolStatus.IN_SERVICE
        model.tools.add(ObservationTool(tool_id, ttype, zone, sens, mode, status))

    tool_ids = [t[0] for t in TOOL_SPECS if t[0] != "RAD-02"]

    print(f"Генерация {n_objects} объектов...")
    catalog_numbers: list[str] = []
    for i in range(1, n_objects + 1):
        number = f"{i:05d}"
        catalog_numbers.append(number)
        otype = OBJECT_TYPES[i % len(OBJECT_TYPES)]
        size = round(random.uniform(0.05, 50.0), 3)
        axis = round(random.uniform(6600, 42000), 1)
        ecc = round(random.uniform(0.0, 0.2), 4)
        incl = round(random.uniform(0, 180), 2)
        silent_days = random.randint(0, 90)
        registered = now - timedelta(days=random.randint(30, 400))
        last_obs = now - timedelta(days=silent_days) if silent_days < 80 else None
        obj = SpaceObject(
            number, _designator(i), otype, size,
            OrbitalElements(axis, ecc, incl), ObjectStatus.CATALOGED,
            registered, last_obs,
        )
        model.objects.add(obj)
        if i % 5000 == 0:
            print(f"  объекты: {i}/{n_objects}")

    print(f"Генерация {n_sessions} сеансов...")
    for i in range(n_sessions):
        number = catalog_numbers[random.randint(0, n_objects - 1)]
        tool_id = tool_ids[i % len(tool_ids)]
        ago_hours = random.randint(1, 120 * 24)
        when = now - timedelta(hours=ago_hours)
        model.sessions.add(ObservationSession(
            None, tool_id, number, when,
            f"az={random.randint(0, 359)} el={random.randint(5, 85)}",
            "Наблюдение принято", "operator",
        ))
        if (i + 1) % 10000 == 0:
            print(f"  сеансы: {i + 1}/{n_sessions}")

    print("Генерация журнала...")
    for i, number in enumerate(catalog_numbers):
        obj = model.objects.get(number)
        model.journal.add(JournalEntry(
            None, EventType.REGISTERED, number, obj.registered_at,
            f"Регистрация {_designator(i + 1)}",
        ))

    lost_count = max(1, n_objects // 10)
    for i in range(lost_count):
        number = catalog_numbers[i * 7 % n_objects]
        lost_at = now - timedelta(days=random.randint(5, 60))
        model.journal.add(JournalEntry(
            None, EventType.LOST, number, lost_at,
            "Нет наблюдений более 30 сут.",
        ))
        if i < lost_count // 3:
            redisc_at = lost_at + timedelta(days=random.randint(1, 20))
            model.journal.add(JournalEntry(
                None, EventType.REDISCOVERED, number, redisc_at,
                "Обнаружен средством RAD-01",
            ))

    n_j = len(model.journal.get_all())
    print(f"Готово: объектов={n_objects}, сеансов={n_sessions}, журнал={n_j}")
    print(f"БД: {db_path} ({os.path.getsize(db_path) / 1024 / 1024:.1f} МБ)")


def main() -> None:
    p = argparse.ArgumentParser(description="Генерация нагрузочных данных")
    p.add_argument("--objects", type=int, default=10000)
    p.add_argument("--sessions", type=int, default=30000)
    p.add_argument("--db", default=os.path.join(ROOT, "data", "perf", "load.db"))
    args = p.parse_args()
    generate(args.db, args.objects, args.sessions)


if __name__ == "__main__":
    main()