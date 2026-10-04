"""Демонстрационные данные (создаются при первом запуске)."""
from datetime import datetime, timedelta

from model.container import ModelContainer
from model.entities import (CoverageZone, ObservationSession, ObservationTool,
                            OrbitalElements, SpaceObject, User)
from model.enums import (ObjectStatus, ObjectType, OperatingMode, ToolStatus, ToolType,
                         UserRole)
from model.services.auth_service import AuthService

DEMO_PASSWORD = "1234"


def seed_demo_data(model: ModelContainer, now: datetime) -> None:
    """Заполнить пустую базу пользователями, средствами и объектами."""
    if model.users.get_all():
        return
    hash_ = AuthService.hash_password(DEMO_PASSWORD)
    for login, name, role in [
        ("operator", "Иванов И. И.", UserRole.OBSERVER_OPERATOR),
        ("analyst", "Петрова А. С.", UserRole.ORBIT_ANALYST),
        ("head", "Сидоров П. А.", UserRole.CENTER_HEAD),
        ("admin", "Админов А. А.", UserRole.ADMIN),
    ]:
        model.users.add(User(login, hash_, name, role))

    for tool in [
        ObservationTool("RAD-01", ToolType.RADAR, CoverageZone(200, 2000, 0, 100), 0.1,
                        OperatingMode.SURVEY, ToolStatus.IN_SERVICE),
        ObservationTool("OPT-01", ToolType.OPTICAL_TELESCOPE, CoverageZone(300, 6000, 0, 120),
                        0.5, OperatingMode.TRACKING, ToolStatus.IN_SERVICE),
        ObservationTool("LAS-01", ToolType.LASER_RANGEFINDER, CoverageZone(300, 1500, 40, 110),
                        0.3, OperatingMode.DEBRIS_SEARCH, ToolStatus.IN_SERVICE),
        ObservationTool("RAD-02", ToolType.RADAR, CoverageZone(200, 1500, 0, 100), 0.1,
                        OperatingMode.SURVEY, ToolStatus.FAILED),
    ]:
        model.tools.add(tool)

    def days_ago(n: float) -> datetime:
        return now - timedelta(days=n)

    # (номер, идентификатор, тип, размер, большая полуось, наклонение, дней без наблюдений)
    objects = [
        ("00001", "1998-067A", ObjectType.ACTIVE_SATELLITE, 100.0, 6790, 51.6, 2),
        ("00002", "2009-005AB", ObjectType.FRAGMENT, 0.3, 7200, 86.4, 45),
        ("00003", "1993-036B", ObjectType.ROCKET_STAGE, 8.0, 7171, 98.7, 60),
        ("00004", "2012-044C", ObjectType.FRAGMENT, 0.08, 7400, 97.0, 10),
        ("00005", "2005-018A", ObjectType.DECOMMISSIONED, 2.0, 7000, 53.0, 5),
    ]
    for number, designator, otype, size, axis, incl, silent_days in objects:
        obj = SpaceObject(number, designator, otype, size, OrbitalElements(axis, 0.001, incl),
                          ObjectStatus.CATALOGED, registered_at=days_ago(120),
                          last_observed_at=days_ago(silent_days))
        model.objects.add(obj)

    # Несколько прошлых сеансов, чтобы в отчёте было «среднее время между наблюдениями».
    history = [("00001", "OPT-01", 2), ("00001", "OPT-01", 5), ("00001", "OPT-01", 9),
               ("00005", "OPT-01", 5), ("00005", "OPT-01", 11),
               ("00004", "LAS-01", 10), ("00004", "LAS-01", 14)]
    for number, tool_id, ago in history:
        model.sessions.add(ObservationSession(
            None, tool_id, number, days_ago(ago), "Дальность, азимут, угол места", "Наблюдение принято",
            "operator"))
