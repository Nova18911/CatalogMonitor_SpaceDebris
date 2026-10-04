"""Общая часть контроллеров: единая обработка ошибок."""
import functools

from controller.session import Session
from model.exceptions import DomainError
from view.interfaces import IView


def safe(method):
    """Перехватывает ошибки Модели и ввода и показывает их во View."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except DomainError as error:
            self.view.show_error(str(error))
        except ValueError as error:
            self.view.show_error(f"Некорректный ввод: {error}")
    return wrapper


class BaseController:
    def __init__(self, session: Session, view: IView) -> None:
        self.session = session
        self.view = view
