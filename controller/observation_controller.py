"""Сценарий «Проведение наблюдения»."""
from controller.base import BaseController, safe
from controller.parsing import parse_datetime
from controller.session import Session
from model.services.observation_service import ObservationService
from view.forms import ObservationForm
from view.interfaces import IView


class ObservationController(BaseController):
    def __init__(self, session: Session, view: IView, service: ObservationService) -> None:
        super().__init__(session, view)
        self._service = service

    @safe
    def refresh_observations(self) -> None:
        self.view.show_tools(self._service.list_tools(self.session.user))
        self.view.show_sessions(self._service.list_sessions(self.session.user))

    @safe
    def add_observation(self, form: ObservationForm) -> None:
        session = self._service.register_session(
            self.session.user, form.tool_id, form.catalog_number,
            parse_datetime(form.observed_at, "Время"), form.raw_data)
        self.view.reset_observation_form()
        self.view.show_info(f"Объект {session.catalog_number}: {session.result}")
