"""Экранные формы на tkinter (стандартная библиотека, ничего устанавливать не нужно).

Представление не содержит бизнес-логики: оно показывает данные и передаёт
введённое в Контроллер через ``IViewHandler``.
"""
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from model.access import Action
from model.dto import ReportData, SessionDto, SpaceObjectDto, ToolDto, UserDto
from model.enums import ObjectType
from view.forms import NewObjectForm, ObservationForm, PeriodForm
from view.interfaces import IView, IViewHandler
from view.report_format import format_report


def _fill_tree(tree: ttk.Treeview, rows: list[tuple]) -> None:
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert("", "end", values=row)


def _make_tree(parent, columns: list[tuple[str, int]], height: int) -> ttk.Treeview:
    """Таблица с вертикальной прокруткой. columns: (заголовок, ширина)."""
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", height=height)
    for title, width in columns:
        tree.heading(title, text=title)
        tree.column(title, width=width, anchor="w")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return tree


def _field(parent, label: str, row: int, column: int = 0, width: int = 22) -> tk.StringVar:
    var = tk.StringVar()
    ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=4, pady=3)
    ttk.Entry(parent, textvariable=var, width=width).grid(
        row=row, column=column + 1, sticky="w", padx=4, pady=3)
    return var


class LoginFrame(ttk.Frame):
    def __init__(self, master, handler: IViewHandler) -> None:
        super().__init__(master, padding=40)
        box = ttk.LabelFrame(self, text="Вход в систему", padding=20)
        box.place(relx=0.5, rely=0.4, anchor="center")
        self._login = _field(box, "Логин", 0)
        self._password = tk.StringVar()
        ttk.Label(box, text="Пароль").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        entry = ttk.Entry(box, textvariable=self._password, show="*", width=22)
        entry.grid(row=1, column=1, padx=4, pady=3)
        ttk.Button(box, text="Войти",
                   command=lambda: handler.login(self._login.get(), self._password.get())
                   ).grid(row=2, column=0, columnspan=2, pady=(10, 0))
        ttk.Label(box, foreground="gray",
                  text="Демо: operator, analyst, head, admin; пароль 1234"
                  ).grid(row=3, column=0, columnspan=2, pady=(10, 0))
        entry.bind("<Return>", lambda _e: handler.login(self._login.get(), self._password.get()))


class CatalogTab(ttk.Frame):
    COLUMNS = [("Номер", 70), ("Междунар. ID", 110), ("Тип", 230), ("Размер, м", 85),
               ("Высота, км", 95), ("Наклон., °", 90), ("Статус", 140),
               ("Посл. наблюдение", 150)]

    def __init__(self, master, handler: IViewHandler, actions: list[Action]) -> None:
        super().__init__(master, padding=8)
        self._tree = _make_tree(self, self.COLUMNS, height=10)

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=6)
        ttk.Button(buttons, text="Обновить", command=handler.refresh_catalog).pack(side="left")
        if Action.CHECK_LOST in actions:
            ttk.Button(buttons, text="Проверить утерянные",
                       command=handler.check_lost).pack(side="left", padx=6)

        self._form_vars = None
        if Action.REGISTER_OBJECT in actions:
            box = ttk.LabelFrame(self, text="Регистрация нового объекта", padding=8)
            box.pack(fill="x")
            self._designator = _field(box, "Междунар. идентификатор", 0, 0)
            ttk.Label(box, text="Тип объекта").grid(row=0, column=2, sticky="w", padx=4)
            self._type = tk.StringVar()
            ttk.Combobox(box, textvariable=self._type, state="readonly", width=26,
                         values=[t.label for t in ObjectType]).grid(row=0, column=3, padx=4)
            self._size = _field(box, "Размер, м (больше 0)", 1, 0)
            self._axis = _field(box, "Большая полуось, км (больше 6371)", 1, 2)
            self._ecc = _field(box, "Эксцентриситет (0–1)", 2, 0)
            self._incl = _field(box, "Наклонение, ° (0–180)", 2, 2)
            ttk.Button(box, text="Зарегистрировать", command=lambda: handler.register_object(
                NewObjectForm(self._designator.get(), self._type.get(), self._size.get(),
                              self._axis.get(), self._ecc.get(), self._incl.get()))
                       ).grid(row=3, column=0, columnspan=2, pady=(6, 0), sticky="w", padx=4)

    def show_objects(self, objects: list[SpaceObjectDto]) -> None:
        _fill_tree(self._tree, [(o.catalog_number, o.intl_designator, o.type_label, o.size_m,
                                 o.altitude_km, o.inclination_deg, o.status_label,
                                 o.last_observed) for o in objects])

    def reset_form(self) -> None:
        if hasattr(self, "_designator"):
            for var in (self._designator, self._type, self._size, self._axis, self._ecc,
                        self._incl):
                var.set("")


class ObservationTab(ttk.Frame):
    COLUMNS = [("Время", 130), ("Средство", 80), ("Объект", 80), ("Оператор", 90),
               ("Результат", 330)]

    def __init__(self, master, handler: IViewHandler) -> None:
        super().__init__(master, padding=8)
        self._tool_ids: dict[str, str] = {}

        box = ttk.LabelFrame(self, text="Новое наблюдение", padding=8)
        box.pack(fill="x")
        ttk.Label(box, text="Средство наблюдения").grid(row=0, column=0, sticky="w", padx=4)
        self._tool = tk.StringVar()
        self._tool_box = ttk.Combobox(box, textvariable=self._tool, state="readonly", width=52)
        self._tool_box.grid(row=0, column=1, columnspan=3, sticky="w", padx=4, pady=3)
        self._number = _field(box, "Каталожный номер", 1, 0)
        self._time = _field(box, "Время (пусто = сейчас)", 1, 2, width=18)
        self._data = _field(box, "Полученные данные", 2, 0, width=40)
        ttk.Button(box, text="Записать наблюдение", command=lambda: handler.add_observation(
            ObservationForm(self._tool_ids.get(self._tool.get(), ""), self._number.get(),
                            self._time.get(), self._data.get()))
                   ).grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 0))

        ttk.Label(self, text="Последние наблюдения").pack(anchor="w", pady=(10, 2))
        self._tree = _make_tree(self, self.COLUMNS, height=8)

    def show_tools(self, tools: list[ToolDto]) -> None:
        self._tool_ids = {t.description: t.tool_id for t in tools}
        self._tool_box["values"] = list(self._tool_ids)

    def show_sessions(self, sessions: list[SessionDto]) -> None:
        _fill_tree(self._tree, [(s.observed_at, s.tool_id, s.catalog_number, s.operator,
                                 s.result) for s in sessions])

    def reset_form(self) -> None:
        for var in (self._number, self._time, self._data):
            var.set("")


class ReportTab(ttk.Frame):
    def __init__(self, master, handler: IViewHandler) -> None:
        super().__init__(master, padding=8)
        box = ttk.LabelFrame(self, text="Период отчёта", padding=8)
        box.pack(fill="x")
        self._from = _field(box, "С (ГГГГ-ММ-ДД)", 0, 0, width=14)
        self._to = _field(box, "По (ГГГГ-ММ-ДД)", 0, 2, width=14)
        self._to.set(date.today().isoformat())
        self._from.set((date.today() - timedelta(days=30)).isoformat())
        ttk.Button(box, text="Сформировать отчёт", command=lambda: handler.build_report(
            PeriodForm(self._from.get(), self._to.get()))).grid(row=0, column=4, padx=10)
        self._text = tk.Text(self, height=18, state="disabled", wrap="word")
        self._text.pack(fill="both", expand=True, pady=(8, 0))

    def show_report(self, report: ReportData) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", format_report(report))
        self._text.configure(state="disabled")


class MainFrame(ttk.Frame):
    def __init__(self, master, handler: IViewHandler, user: UserDto,
                 actions: list[Action]) -> None:
        super().__init__(master, padding=8)
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text=f"{user.full_name} — {user.role.label}").pack(side="left")
        ttk.Button(header, text="Выйти", command=handler.logout).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, pady=(8, 0))
        self.catalog = self.observation = self.report = None
        if Action.VIEW_CATALOG in actions:
            self.catalog = CatalogTab(notebook, handler, actions)
            notebook.add(self.catalog, text="Каталог")
        if Action.ADD_OBSERVATION in actions:
            self.observation = ObservationTab(notebook, handler)
            notebook.add(self.observation, text="Наблюдения")
        if Action.BUILD_REPORT in actions:
            self.report = ReportTab(notebook, handler)
            notebook.add(self.report, text="Отчёт")
        if not notebook.tabs():
            ttk.Label(self, text="Для вашей роли в этой версии нет доступных функций."
                      ).pack(pady=20)


class TkView(IView):
    """Главное окно приложения."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Каталогизация и мониторинг космического мусора")
        self.root.geometry("1040x640")
        self._handler: IViewHandler | None = None
        self._frame: ttk.Frame | None = None
        self._main: MainFrame | None = None

    def set_handler(self, handler: IViewHandler) -> None:
        self._handler = handler

    def run(self) -> None:
        self.root.mainloop()

    def _show(self, frame: ttk.Frame) -> None:
        if self._frame is not None:
            self._frame.destroy()
        self._frame = frame
        frame.pack(fill="both", expand=True)

    def show_login(self) -> None:
        self._main = None
        self._show(LoginFrame(self.root, self._handler))

    def show_main(self, user: UserDto, actions: list[Action]) -> None:
        self._main = MainFrame(self.root, self._handler, user, actions)
        self._show(self._main)

    def show_objects(self, objects: list[SpaceObjectDto]) -> None:
        if self._main and self._main.catalog:
            self._main.catalog.show_objects(objects)

    def show_tools(self, tools: list[ToolDto]) -> None:
        if self._main and self._main.observation:
            self._main.observation.show_tools(tools)

    def show_sessions(self, sessions: list[SessionDto]) -> None:
        if self._main and self._main.observation:
            self._main.observation.show_sessions(sessions)

    def show_report(self, report: ReportData) -> None:
        if self._main and self._main.report:
            self._main.report.show_report(report)

    def reset_object_form(self) -> None:
        if self._main and self._main.catalog:
            self._main.catalog.reset_form()

    def reset_observation_form(self) -> None:
        if self._main and self._main.observation:
            self._main.observation.reset_form()

    def show_info(self, text: str) -> None:
        messagebox.showinfo("Сообщение", text)

    def show_error(self, text: str) -> None:
        messagebox.showerror("Ошибка", text)
