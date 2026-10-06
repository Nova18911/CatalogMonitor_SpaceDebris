"""Сценарий «Проведение наблюдения»."""
from controller.base import BaseController, safe
from controller.parsing import parse_datetime, parse_float
from controller.session import Session
from model.entities import OrbitalElements
from model.enums import ObjectType
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
        # Если заполнены поля нового объекта — передаём их в сервис
        extra_kwargs = {}
        if form.intl_designator.strip() or form.type_label.strip() or form.size_m.strip():
            if not form.type_label.strip():
                raise ValueError("выберите тип объекта")
            extra_kwargs = {
                "intl_designator": form.intl_designator,
                "object_type": ObjectType.from_label(form.type_label),
                "size_m": parse_float(form.size_m, "Размер"),
                "elements": OrbitalElements(
                    parse_float(form.semi_major_axis_km, "Большая полуось"),
                    parse_float(form.eccentricity, "Эксцентриситет"),
                    parse_float(form.inclination_deg, "Наклонение"),
                ),
            }

        session = self._service.register_session(
            self.session.user,
            form.tool_id,
            form.catalog_number,
            parse_datetime(form.observed_at, "Время"),
            form.raw_data,
            **extra_kwargs,
        )
        self.view.reset_observation_form()
        self.view.show_info(f"Объект {session.catalog_number}: {session.result}")