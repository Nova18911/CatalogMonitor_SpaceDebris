"""Сценарий «Формирование отчёта»."""
from controller.base import BaseController, safe
from controller.parsing import parse_day_end, parse_day_start
from controller.session import Session
from model.services.report_service import ReportService
from view.forms import PeriodForm
from view.interfaces import IView


class ReportController(BaseController):
    def __init__(self, session: Session, view: IView, service: ReportService) -> None:
        super().__init__(session, view)
        self._service = service

    @safe
    def build_report(self, form: PeriodForm) -> None:
        report = self._service.build_report(
            self.session.user, parse_day_start(form.date_from, "С"),
            parse_day_end(form.date_to, "По"))
        self.view.show_report(report)
