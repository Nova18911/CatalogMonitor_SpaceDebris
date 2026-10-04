"""Интерфейсы между Представлением и Контроллером.

* ``IViewHandler`` — что Представление вызывает у Контроллера (нажатия кнопок).
* ``IView`` — что Контроллер вызывает у Представления (показать данные, сообщение).

Благодаря им окно на tkinter можно заменить на консоль или веб-страницу,
не меняя Контроллер и Модель.
"""
from abc import ABC, abstractmethod

from model.access import Action
from model.dto import ReportData, SessionDto, SpaceObjectDto, ToolDto, UserDto
from view.forms import NewObjectForm, ObservationForm, PeriodForm


class IViewHandler(ABC):
    """Обработчики действий пользователя (реализует Контроллер)."""

    @abstractmethod
    def login(self, login: str, password: str) -> None: ...

    @abstractmethod
    def logout(self) -> None: ...

    @abstractmethod
    def refresh_catalog(self) -> None: ...

    @abstractmethod
    def register_object(self, form: NewObjectForm) -> None: ...

    @abstractmethod
    def check_lost(self) -> None: ...

    @abstractmethod
    def add_observation(self, form: ObservationForm) -> None: ...

    @abstractmethod
    def build_report(self, form: PeriodForm) -> None: ...


class IView(ABC):
    """Что умеет показывать Представление (вызывает Контроллер)."""

    @abstractmethod
    def set_handler(self, handler: IViewHandler) -> None: ...

    @abstractmethod
    def run(self) -> None: ...

    @abstractmethod
    def show_login(self) -> None: ...

    @abstractmethod
    def show_main(self, user: UserDto, actions: list[Action]) -> None: ...

    @abstractmethod
    def show_objects(self, objects: list[SpaceObjectDto]) -> None: ...

    @abstractmethod
    def show_tools(self, tools: list[ToolDto]) -> None: ...

    @abstractmethod
    def show_sessions(self, sessions: list[SessionDto]) -> None: ...

    @abstractmethod
    def show_report(self, report: ReportData) -> None: ...

    @abstractmethod
    def reset_object_form(self) -> None: ...

    @abstractmethod
    def reset_observation_form(self) -> None: ...

    @abstractmethod
    def show_info(self, text: str) -> None: ...

    @abstractmethod
    def show_error(self, text: str) -> None: ...
