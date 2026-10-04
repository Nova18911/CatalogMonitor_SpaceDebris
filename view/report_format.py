"""Текстовое оформление отчёта. Отсутствие данных показывается как «нет данных»."""
from model.dto import Metric, ReportData

NO_DATA = "нет данных"


def _share(m: Metric) -> str:
    if m.value is None:
        return NO_DATA
    if m.numerator is None:
        return f"{m.value * 100:.1f} %"
    return f"{m.value * 100:.1f} % ({m.numerator} из {m.denominator})"


def format_report(r: ReportData) -> str:
    lines = [f"ОТЧЁТ ЗА ПЕРИОД {r.period_from:%Y-%m-%d} — {r.period_to:%Y-%m-%d}", ""]

    lines.append("1. Количество каталогизированных объектов по типам:")
    if r.counts_by_type is None:
        lines.append(f"     {NO_DATA}")
    else:
        lines += [f"     {label}: {count}" for label, count in r.counts_by_type.items()]

    approaches = NO_DATA if r.dangerous_approaches is None else str(r.dangerous_approaches)
    lines.append(f"2. Количество опасных сближений за период: {approaches}")
    lines.append(f"3. Доля утерянных объектов: {_share(r.lost_share)}")
    lines.append(f"4. Доля повторно обнаруженных объектов: {_share(r.rediscovered_share)}")
    lines.append("5. Охват орбитального пространства средствами наблюдения: "
                 f"{_share(r.orbit_coverage)}")

    gap = r.avg_gap_hours
    gap_text = (NO_DATA if gap.value is None
                else f"{gap.value:.1f} ч (по объектам: {gap.denominator})")
    lines.append(f"6. Среднее время между наблюдениями по объектам: {gap_text}")
    return "\n".join(lines)
