"""Формы ввода: то, что пользователь ввёл на экране, в виде строк.

Преобразованием строк в числа и даты занимается Контроллер.
"""
from dataclasses import dataclass


@dataclass
class NewObjectForm:
    intl_designator: str
    type_label: str
    size_m: str
    semi_major_axis_km: str
    eccentricity: str
    inclination_deg: str


@dataclass
class ObservationForm:
    tool_id: str
    catalog_number: str
    observed_at: str      # пусто = сейчас
    raw_data: str
    # --- если объект отсутствует в каталоге ---
    intl_designator: str = ""
    type_label: str = ""
    size_m: str = ""
    semi_major_axis_km: str = ""
    eccentricity: str = ""
    inclination_deg: str = ""


@dataclass
class PeriodForm:
    date_from: str        # ГГГГ-ММ-ДД
    date_to: str
