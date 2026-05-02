import datetime
import calendar
import tkinter.messagebox as msg
import customtkinter as ctk

from shared.utils.dateUtils import parse_date_input

class DatePickerDialog(ctk.CTkToplevel):
    """
    Модальный диалог выбора даты с календарём и полем ручного ввода.

    Использование:
        result = DatePickerDialog.ask(master, initial_date="2024-03-15")
        if result:
            print(result)  # "2024-03-15"
    """

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
        x = (
            self.master.winfo_rootx()
            + (self.master.winfo_width() - self.winfo_width()) // 2
        )
        y = (
            self.master.winfo_rooty()
            + (self.master.winfo_height() - self.winfo_height()) // 2
        )
        self.geometry(f"+{x}+{y}")

    def _build(self):
        pad = {"padx": 8, "pady": 4}

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", **pad)
        ctk.CTkLabel(top, text="Дата (ДД.ММ.ГГГГ):").pack(side="left")
        self._entry = ctk.CTkEntry(top, width=120)
        self._entry.pack(side="left", padx=6)
        self._entry.insert(0, self._date.strftime("%d.%m.%Y"))
        ctk.CTkButton(top, text="✓", width=36, command=self._from_entry).pack(side="left")

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="x", **pad)
        ctk.CTkButton(nav, text="◀", width=32, command=self._prev_month).pack(side="left")
        self._month_lbl = ctk.CTkLabel(nav, text="", width=160)
        self._month_lbl.pack(side="left", expand=True)
        ctk.CTkButton(nav, text="▶", width=32, command=self._next_month).pack(
            side="right"
        )

        self._cal_frame = ctk.CTkFrame(self)
        self._cal_frame.pack(fill="both", expand=True, **pad)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", **pad)
        ctk.CTkButton(btn_row, text="Сегодня", command=self._today).pack(side="left")
        ctk.CTkButton(
            btn_row, text="Отмена", fg_color="gray30", command=self.destroy
        ).pack(side="right", padx=4)
        ctk.CTkButton(btn_row, text="OK", command=self._ok).pack(side="right")

        self._render_calendar()

    def _render_calendar(self):
        for w in self._cal_frame.winfo_children():
            w.destroy()

        self._month_lbl.configure(
            text=f"{self._view_year}  {calendar.month_name[self._view_month]}"
        )
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for c, d in enumerate(days):
            ctk.CTkLabel(
                self._cal_frame, text=d, width=36, font=ctk.CTkFont(weight="bold")
            ).grid(row=0, column=c, padx=1, pady=1)

        first_wd, num_days = calendar.monthrange(self._view_year, self._view_month)
        row, col = 1, first_wd
        for day in range(1, num_days + 1):
            is_sel = (
                day == self._date.day
                and self._view_month == self._date.month
                and self._view_year == self._date.year
            )
            fg = "#2b579a" if is_sel else "gray25"
            btn = ctk.CTkButton(
                self._cal_frame,
                text=str(day),
                width=36,
                height=28,
                fg_color=fg,
                hover_color="#1f427a",
                command=lambda dd=day: self._pick(dd),
            )
            btn.grid(row=row, column=col, padx=1, pady=1)
            col += 1
            if col == 7:
                col, row = 0, row + 1

    def _pick(self, day: int):
        self._date = datetime.date(self._view_year, self._view_month, day)
        self._entry.delete(0, "end")
        self._entry.insert(0, self._date.strftime("%d.%m.%Y"))
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

    def _from_entry(self):
        iso = parse_date_input(self._entry.get())
        if iso:
            d = datetime.date.fromisoformat(iso)
            self._date = d
            self._view_year, self._view_month = d.year, d.month
            self._render_calendar()
        else:
            msg.showwarning("Ошибка", "Неверный формат даты. Введите ДД.ММ.ГГГГ")

    def _ok(self):
        self.result = self._date.isoformat()
        self.destroy()

    @classmethod
    def ask(cls, master, initial_date=None, title="Выберите дату") -> str | None:
        dlg = cls(master, initial_date, title)
        master.wait_window(dlg)
        return dlg.result
