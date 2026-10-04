"""Точка входа: собирает Модель, Представление и Контроллер и запускает окно."""
import os

from controller.app_controller import ApplicationController
from model.container import build_model, system_clock
from model.seed import seed_demo_data
from view.tk_view import TkView

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "catalog.db")


def main() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    model = build_model(DB_PATH)
    seed_demo_data(model, system_clock())
    ApplicationController(TkView(), model).start()


if __name__ == "__main__":
    main()
