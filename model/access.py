"""Права ролей. Проверяются в сервисах Модели, а не в интерфейсе."""
from enum import Enum

from model.enums import UserRole
from model.exceptions import AccessDeniedError


class Action(Enum):
    VIEW_CATALOG = "Просмотр каталога"
    REGISTER_OBJECT = "Регистрация объекта"
    ADD_OBSERVATION = "Проведение наблюдения"
    CHECK_LOST = "Проверка утерянных объектов"
    BUILD_REPORT = "Формирование отчёта"


_RIGHTS = {
    UserRole.OBSERVER_OPERATOR: {Action.VIEW_CATALOG, Action.ADD_OBSERVATION},
    UserRole.ORBIT_ANALYST: {Action.VIEW_CATALOG, Action.REGISTER_OBJECT, Action.CHECK_LOST},
    # Руководитель не производит наблюдения лично; отчёты формирует только он.
    UserRole.CENTER_HEAD: {Action.VIEW_CATALOG, Action.REGISTER_OBJECT,
                           Action.CHECK_LOST, Action.BUILD_REPORT},
    UserRole.ADMIN: {Action.VIEW_CATALOG, Action.REGISTER_OBJECT, Action.CHECK_LOST},
}


class AccessPolicy:
    """Правила доступа «роль -> действия»."""

    def allowed_actions(self, role: UserRole) -> list[Action]:
        rights = _RIGHTS.get(role, set())
        return [a for a in Action if a in rights]

    def check(self, role: UserRole, action: Action) -> None:
        if action not in _RIGHTS.get(role, set()):
            raise AccessDeniedError(
                f"Роли «{role.label}» недоступно действие «{action.value}»")
