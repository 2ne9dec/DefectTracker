import datetime
import calendar
import customtkinter as ctk

from shared.utils.dateUtils import parse_date_input

class InlineDatePicker(ctk.CTkToplevel):
    """
    Всплывающий календарь, привязанный к виджету-якорю.
    Появляется прямо под инпутом, закрывается по ESC или клику вне окна.
    """

    def __init__(self, master, anchor_widget, date_var: ctk.StringVar, initial_iso: str | None = None):
        super().__init__(master)

        self.transient(master)
        self.resizable(False, False)
        # Скрываем стандартный заголовок окна
        self.after(10, lambda: self.wm_overrideredirect(True))

        self._date_var = date_var
        today = datetime.date.today()

        if initial_iso:
            try:
                self._date = datetime.date.fromisoformat(initial_iso)
            except ValueError:
                self._date = today
        else:
            self._date = today

        self._view_year = self._date.year
        self._view_month = self._date.month
        self._anchor = anchor_widget
        self._toplevel = master.winfo_toplevel()

        self._build()
        self.update_idletasks()
        self._position_under(anchor_widget)

        # ESC закрывает — вешаем и на само окно, и на toplevel
        self.bind("<Escape>", lambda e: self._close())
        self._toplevel.bind("<Escape>", lambda e: self._close(), add="+")
        # Клик вне окна — вешаем на toplevel с задержкой чтобы не поймать текущий клик
        self.after(200, self._bind_outside_click)
        # Забираем фокус клавиатуры после появления окна
        self.after(50, self.focus_force)

    def _bind_outside_click(self):
        self._click_id = self._toplevel.bind("<Button-1>", self._on_root_click, add="+")

    def _position_under(self, widget):
        widget.update_idletasks()
        x = widget.winfo_rootx()
        y = widget.winfo_rooty() + widget.winfo_height() + 2
        self.geometry(f"+{x}+{y}")

    def _on_root_click(self, event):
        try:
            wx = self.winfo_rootx()
            wy = self.winfo_rooty()
            ww = self.winfo_width()
            wh = self.winfo_height()
            if not (wx <= event.x_root <= wx + ww and wy <= event.y_root <= wy + wh):
                self._close()
        except Exception:
            self._close()

    def _close(self):
        try:
            self._toplevel.unbind("<Button-1>", self._click_id)
        except Exception:
            pass
        try:
            self._toplevel.unbind("<Escape>")
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _build(self):
        # Навигация по месяцам
        nav = ctk.CTkFrame(self, fg_color="#1e2a3a", corner_radius=0)
        nav.pack(fill="x")
        ctk.CTkButton(
            nav, text="◀", width=28, height=26, fg_color="transparent", hover_color="gray30", command=self._prev_month
        ).pack(side="left", padx=2)
        self._month_lbl = ctk.CTkLabel(nav, text="", width=160, font=ctk.CTkFont(size=12, weight="bold"))
        self._month_lbl.pack(side="left", expand=True)
        ctk.CTkButton(
            nav, text="▶", width=28, height=26, fg_color="transparent", hover_color="gray30", command=self._next_month
        ).pack(side="right", padx=2)

        self._cal_frame = ctk.CTkFrame(self, fg_color="#1a2332", corner_radius=0)
        self._cal_frame.pack(padx=6, pady=(2, 4))

        # Кнопка "Сегодня"
        ctk.CTkButton(
            self, text="Сегодня", height=26, fg_color="gray25", hover_color="gray35", command=self._today
        ).pack(fill="x", padx=6, pady=(0, 6))

        self._render_calendar()

    def _render_calendar(self):
        for w in self._cal_frame.winfo_children():
            w.destroy()

        self._month_lbl.configure(text=f"{calendar.month_name[self._view_month]} {self._view_year}")

        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for c, d in enumerate(days):
            ctk.CTkLabel(
                self._cal_frame,
                text=d,
                width=32,
                height=24,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="gray60",
            ).grid(row=0, column=c, padx=1, pady=1)

        first_wd, num_days = calendar.monthrange(self._view_year, self._view_month)
        row, col = 1, first_wd
        for day in range(1, num_days + 1):
            is_sel = (
                day == self._date.day and self._view_month == self._date.month and self._view_year == self._date.year
            )
            btn = ctk.CTkButton(
                self._cal_frame,
                text=str(day),
                width=32,
                height=26,
                fg_color="#2b579a" if is_sel else "gray22",
                hover_color="#3a6abf",
                font=ctk.CTkFont(size=11),
                command=lambda dd=day: self._pick(dd),
            )
            btn.grid(row=row, column=col, padx=1, pady=1)
            col += 1
            if col == 7:
                col, row = 0, row + 1

    def _pick(self, day: int):
        self._date = datetime.date(self._view_year, self._view_month, day)
        self._date_var.set(self._date.strftime("%d.%m.%Y"))
        self._close()

    def _prev_month(self):
        if self._view_month == 1:
            self._view_year -= 1
            self._view_month = 12
        else:
            self._view_month -= 1
        self._render_calendar()

    def _next_month(self):
        if self._view_month == 12:
            self._view_year += 1
            self._view_month = 1
        else:
            self._view_month += 1
        self._render_calendar()

    def _today(self):
        t = datetime.date.today()
        self._view_year, self._view_month = t.year, t.month
        self._pick(t.day)


# Оставляем старый DatePickerDialog для совместимости (используется в fixDefectDialog)
class DatePickerDialog(ctk.CTkToplevel):
    """Модальный диалог выбора даты (используется в диалоге устранения)."""

    def __init__(self, master, initial_date: str | None = None, title="Выберите дату"):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result: str | None = None

        today = datetime.date.today()
        if initial_date:
            try:
                self._date = datetime.date.fromisoformat(initial_date)
            except ValueError:
                self._date = today
        else:
            self._date = today

        self._view_year = self._date.year
        self._view_month = self._date.month
        self._build()
        self.after(100, self._center)

    def _center(self):
        self.update_idletasks()
        x = self.master.winfo_rootx() + (self.master.winfo_width() - self.winfo_width()) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build(self):
        pad = {"padx": 8, "pady": 4}
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", **pad)
        ctk.CTkButton(nav, text="◀", width=32, command=self._prev_month).pack(side="left")
        self._month_lbl = ctk.CTkLabel(nav, text="", width=160)
        self._month_lbl.pack(side="left", expand=True)
        ctk.CTkButton(nav, text="▶", width=32, command=self._next_month).pack(side="right")

        self._cal_frame = ctk.CTkFrame(self)
        self._cal_frame.pack(fill="both", expand=True, **pad)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", **pad)
        ctk.CTkButton(btn_row, text="Сегодня", command=self._today).pack(side="left")
        ctk.CTkButton(btn_row, text="Отмена", fg_color="gray30", command=self.destroy).pack(side="right", padx=4)
        ctk.CTkButton(btn_row, text="OK", command=self._ok).pack(side="right")
        self._render_calendar()

    def _render_calendar(self):
        for w in self._cal_frame.winfo_children():
            w.destroy()
        self._month_lbl.configure(text=f"{self._view_year}  {calendar.month_name[self._view_month]}")
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for c, d in enumerate(days):
            ctk.CTkLabel(self._cal_frame, text=d, width=36, font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=c, padx=1, pady=1
            )
        first_wd, num_days = calendar.monthrange(self._view_year, self._view_month)
        row, col = 1, first_wd
        for day in range(1, num_days + 1):
            is_sel = (
                day == self._date.day and self._view_month == self._date.month and self._view_year == self._date.year
            )
            btn = ctk.CTkButton(
                self._cal_frame,
                text=str(day),
                width=36,
                height=28,
                fg_color="#2b579a" if is_sel else "gray25",
                hover_color="#1f427a",
                command=lambda dd=day: self._pick(dd),
            )
            btn.grid(row=row, column=col, padx=1, pady=1)
            col += 1
            if col == 7:
                col, row = 0, row + 1

    def _pick(self, day):
        self._date = datetime.date(self._view_year, self._view_month, day)
        self._render_calendar()

    def _prev_month(self):
        if self._view_month == 1:
            self._view_year -= 1
            self._view_month = 12
        else:
            self._view_month -= 1
        self._render_calendar()

    def _next_month(self):
        if self._view_month == 12:
            self._view_year += 1
            self._view_month = 1
        else:
            self._view_month += 1
        self._render_calendar()

    def _today(self):
        t = datetime.date.today()
        self._view_year, self._view_month = t.year, t.month
        self._pick(t.day)

    def _ok(self):
        self.result = self._date.isoformat()
        self.destroy()

    @classmethod
    def ask(cls, master, initial_date=None, title="Выберите дату") -> str | None:
        dlg = cls(master, initial_date, title)
        master.wait_window(dlg)
        return dlg.result
