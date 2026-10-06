"""Профилирование двух ключевых сценариев (после оптимизаций).

Запуск:
  python scripts/generate_load_data.py --objects 10000 --sessions 30000 --db data/perf/load_10k_fresh.db
  python scripts/profile_scenarios.py --db data/perf/load_10k_fresh.db
"""
from __future__ import annotations

import argparse
import cProfile
import io
import os
import pstats
import sys
import time
import timeit
import tracemalloc
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from model.container import build_model
from model.dto import UserDto
from model.enums import UserRole


def _user_head() -> UserDto:
    return UserDto("head", "Сидоров П. А.", UserRole.CENTER_HEAD)


def _user_analyst() -> UserDto:
    return UserDto("analyst", "Петрова А. С.", UserRole.ORBIT_ANALYST)


def scenario_report(db_path: str) -> dict:
    model = build_model(db_path)
    try:
        now = datetime.now().replace(microsecond=0)
        period_from = now - timedelta(days=90)
        period_to = now
        user = _user_head()

        def run():
            return model.report.build_report(user, period_from, period_to)

        t = timeit.timeit(run, number=3) / 3 * 1000

        tracemalloc.start()
        report = run()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        pr = cProfile.Profile()
        pr.enable()
        run()
        pr.disable()
        buf = io.StringIO()
        stats = pstats.Stats(pr, stream=buf).sort_stats("tottime")
        stats.print_stats(20)
        profile_text = buf.getvalue()

        top5 = []
        for func, (cc, nc, tt, ct, callers) in sorted(
            stats.stats.items(), key=lambda x: x[1][2], reverse=True
        )[:5]:
            top5.append(
                (f"{func[2]}:{func[0].split(os.sep)[-1]}", round(tt * 1000, 2), nc)
            )

        # сколько раз вызывался until (ожидаем 1 на прогон отчёта после оптимизации №1)
        until_calls = sum(
            nc for func, (cc, nc, tt, ct, callers) in stats.stats.items()
            if "until" in str(func[2])
        )

        return {
            "name": "Формирование отчёта за период",
            "n_objects": len(model.objects.get_all()),
            "n_sessions": len(model.sessions.get_all()),
            "n_journal": len(model.journal.get_all()),
            "time_ms": round(t, 1),
            "peak_mb": round(peak / 1024 / 1024, 2),
            "top5": top5,
            "profile_head": "\n".join(profile_text.splitlines()[:25]),
            "until_calls": until_calls,
            "lost_share": report.lost_share.value,
            "rediscovered_share": report.rediscovered_share.value,
            "counts": report.counts_by_type,
        }
    finally:
        model.close()


def scenario_catalog(db_path: str) -> dict:
    model = build_model(db_path)
    try:
        user = _user_analyst()

        # --- холодный check_lost: один раз, отдельно ---
        t0 = time.perf_counter()
        lost_cold = model.catalog.check_lost(user)
        t_cold_ms = (time.perf_counter() - t0) * 1000

        def run():
            objs = model.catalog.list_objects(user)
            lost = model.catalog.check_lost(user)  # уже «тёплый»
            return objs, lost

        t_warm = timeit.timeit(run, number=3) / 3 * 1000

        tracemalloc.start()
        objs, lost = run()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        pr = cProfile.Profile()
        pr.enable()
        run()
        pr.disable()
        buf = io.StringIO()
        stats = pstats.Stats(pr, stream=buf).sort_stats("tottime")
        stats.print_stats(20)
        profile_text = buf.getvalue()

        top5 = []
        for func, (cc, nc, tt, ct, callers) in sorted(
            stats.stats.items(), key=lambda x: x[1][2], reverse=True
        )[:5]:
            top5.append(
                (f"{func[2]}:{func[0].split(os.sep)[-1]}", round(tt * 1000, 2), nc)
            )

        return {
            "name": "Список каталога + проверка утерянных",
            "n_objects": len(model.objects.get_all()),
            "n_sessions": len(model.sessions.get_all()),
            "n_journal": len(model.journal.get_all()),
            "time_ms": round(t_warm, 1),
            "time_cold_check_lost_ms": round(t_cold_ms, 1),
            "newly_lost_cold": len(lost_cold),
            "peak_mb": round(peak / 1024 / 1024, 2),
            "top5": top5,
            "profile_head": "\n".join(profile_text.splitlines()[:25]),
            "listed": len(objs),
            "newly_lost": len(lost),
        }
    finally:
        model.close()


def print_result(r: dict) -> None:
    print("=" * 70)
    print(f"Сценарий: {r['name']}")
    print(f"  Объектов: {r['n_objects']}, сеансов: {r['n_sessions']}, журнал: {r['n_journal']}")
    print(f"  Время (timeit, тёплый): {r['time_ms']} мс")
    if "time_cold_check_lost_ms" in r:
        print(f"  Время check_lost (ХОЛОДНЫЙ, 1 раз): {r['time_cold_check_lost_ms']} мс")
        print(f"  Помечено утерянными (холодный): {r['newly_lost_cold']}")
    if "until_calls" in r:
        print(f"  Вызовов until в cProfile (1 прогон отчёта): {r['until_calls']}")
    if "lost_share" in r:
        print(f"  lost_share={r['lost_share']}, rediscovered_share={r['rediscovered_share']}")
    print(f"  Память (tracemalloc peak): {r['peak_mb']} МБ")
    print("  Топ-5 функций по tottime (cProfile):")
    for name, ms, ncalls in r["top5"]:
        print(f"    {ms:8.2f} мс  ncalls={ncalls:6d}  {name}")
    print("-" * 70)
    print(r["profile_head"])
    print("=" * 70)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--db",
        default=os.path.join(ROOT, "data", "perf", "load_10k.db"),
        help="Путь к SQLite с нагрузочными данными",
    )
    p.add_argument("--scenario", choices=["report", "catalog", "both"], default="both")
    args = p.parse_args()
    if not os.path.exists(args.db):
        print(f"Файл не найден: {args.db}")
        print("Сначала: python scripts/generate_load_data.py --db ...")
        sys.exit(1)

    results = []
    if args.scenario in ("report", "both"):
        r = scenario_report(args.db)
        print_result(r)
        results.append(r)
    if args.scenario in ("catalog", "both"):
        r = scenario_catalog(args.db)
        print_result(r)
        results.append(r)

    print("\n### Сводка для таблицы")
    for r in results:
        extra = ""
        if "time_cold_check_lost_ms" in r:
            extra = f", cold check_lost {r['time_cold_check_lost_ms']} мс"
        print(
            f"| {r['name']} | {r['time_ms']} мс, peak {r['peak_mb']} МБ{extra} |"
        )


if __name__ == "__main__":
    main()