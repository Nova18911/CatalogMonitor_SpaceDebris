"""Главный контроллер: вход, выход, маршрутизация действий и реакция на события Модели."""
from controller.base import BaseController, safe
from controller.catalog_controller import CatalogController
from controller.observation_controller import ObservationController
from controller.report_controller import ReportController
from controller.session import Session
from model.access import Action
from model.container import ModelContainer
from model.events import IModelObserver, ModelEvent
from view.forms import NewObjectForm, ObservationForm, PeriodForm
from view.interfaces import IView, IViewHandler


class ApplicationController(BaseController, IViewHandler, IModelObserver):
    def __init__(self, view: IView, model: ModelContainer) -> None:
        super().__init__(Session(), view)
        self._model = model
        self._catalog = CatalogController(self.session, view, model.catalog)
        self._observation = ObservationController(self.session, view, model.observation)
        self._report = ReportController(self.session, view, model.report)
        model.bus.subscribe(self)
        view.set_handler(self)

    def start(self) -> None:
        self.view.show_login()
        self.view.run()

    # --- вход и выход -------------------------------------------------------
    @safe
    def login(self, login: str, password: str) -> None:
        user = self._model.auth.login(login, password)
        actions = self._model.auth.allowed_actions(user.role)
        self.session.start(user, actions)
        self.view.show_main(user, actions)
        self._refresh_screens()

    def logout(self) -> None:
        self.session.end()
        self.view.show_login()

    # --- действия пользователя передаём профильным контроллерам --------------
    def refresh_catalog(self) -> None:
        self._catalog.refresh_catalog()

    def register_object(self, form: NewObjectForm) -> None:
        self._catalog.register_object(form)

    def check_lost(self) -> None:
        self._catalog.check_lost()

    def add_observation(self, form: ObservationForm) -> None:
        self._observation.add_observation(form)

    def build_report(self, form: PeriodForm) -> None:
        self._report.build_report(form)

    # --- реакция на изменения в Модели ------------------------------------
    def on_model_changed(self, event: ModelEvent) -> None:
        if self.session.user is not None:
            self._refresh_screens()

    def _refresh_screens(self) -> None:
        if self.session.can(Action.VIEW_CATALOG):
            self._catalog.refresh_catalog()
        if self.session.can(Action.ADD_OBSERVATION):
            self._observation.refresh_observations()
