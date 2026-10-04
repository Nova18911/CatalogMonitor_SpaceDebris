"""Вход в систему и список доступных действий."""
import hashlib

from model.access import AccessPolicy, Action
from model.dto import UserDto
from model.enums import UserRole
from model.exceptions import ValidationError
from model.repositories import UserRepository


class AuthService:
    def __init__(self, users: UserRepository, policy: AccessPolicy) -> None:
        self._users = users
        self._policy = policy

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def login(self, login: str, password: str) -> UserDto:
        """Проверить логин и пароль; при ошибке — ValidationError."""
        user = self._users.get(login.strip())
        if user is None or user.password_hash != self.hash_password(password):
            raise ValidationError("Неверный логин или пароль")
        return UserDto(user.login, user.full_name, user.role)

    def allowed_actions(self, role: UserRole) -> list[Action]:
        return self._policy.allowed_actions(role)
