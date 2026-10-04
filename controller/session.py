"""Сессия: кто сейчас вошёл в систему."""
from model.access import Action
from model.dto import UserDto


class Session:
    def __init__(self) -> None:
        self.user: UserDto | None = None
        self.actions: list[Action] = []

    def start(self, user: UserDto, actions: list[Action]) -> None:
        self.user, self.actions = user, actions

    def end(self) -> None:
        self.user, self.actions = None, []

    def can(self, action: Action) -> bool:
        return action in self.actions
