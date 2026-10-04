"""Сценарии «Регистрация объекта» и «Проверка утерянных»."""
from controller.base import BaseController, safe
from controller.parsing import parse_float
from controller.session import Session
from model.entities import OrbitalElements
from model.enums import ObjectType
from model.services.catalog_service import CatalogService
from view.forms import NewObjectForm
from view.interfaces import IView


class CatalogController(BaseController):
    def __init__(self, session: Session, view: IView, service: CatalogService) -> None:
        super().__init__(session, view)
        self._service = service

    @safe
    def refresh_catalog(self) -> None:
        self.view.show_objects(self._service.list_objects(self.session.user))

    @safe
    def register_object(self, form: NewObjectForm) -> None:
        if not form.type_label:
            raise ValueError("выберите тип объекта")
        elements = OrbitalElements(
            parse_float(form.semi_major_axis_km, "Большая полуось"),
            parse_float(form.eccentricity, "Эксцентриситет"),
            parse_float(form.inclination_deg, "Наклонение"))
        obj = self._service.register_object(
            self.session.user, form.intl_designator, ObjectType.from_label(form.type_label),
            parse_float(form.size_m, "Размер"), elements)
        self.view.reset_object_form()
        self.view.show_info(f"Объект зарегистрирован. Каталожный номер: {obj.catalog_number}")

    @safe
    def check_lost(self) -> None:
        lost = self._service.check_lost(self.session.user)
        if lost:
            numbers = ", ".join(o.catalog_number for o in lost)
            self.view.show_info(f"Статус «утерян» присвоен объектам: {numbers}")
        else:
            self.view.show_info("Объектов с превышенным сроком без наблюдений нет")
