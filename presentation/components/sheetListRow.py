import datetime
import tkinter.messagebox as msg
import customtkinter as ctk

from shared.constants import SEVERITY_COLORS, SEVERITY_LABELS
from shared.utils.dateUtils import fmt_date, parse_date_input
from shared.widgets.datePicker import DatePickerDialog, InlineDatePicker

class DetailDialog(ctk.CTkToplevel):
    """
    Модальное окно: список всех дефектов опоры + возможность выбрать и устранить.
    on_fix: Callable(ids, date_fixed, inspector_fix) — вызывается при сохранении.
    """

    def __init__(self, master, pole_num: int, records: list[tuple], on_fix=None):
        super().__init__(master)
        self.title(f"Опора №{pole_num} — дефекты")
        self.geometry("680x560")
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._on_fix = on_fix
        self._cb_vars: dict[int, ctk.BooleanVar] = {}
        self._records = records
        self._has_active = any(not r[7] for r in records)

        self._build(pole_num, records)

    def _build(self, pole_num: int, records: list[tuple]):
        # Заголовок
        ctk.CTkLabel(
            self,
            text=f"Опора №{pole_num}",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(12, 2))

        if self._has_active and self._on_fix:
            ctk.CTkLabel(
                self,
                text="Отметьте дефекты для устранения и нажмите «Устранить»",
                font=ctk.CTkFont(size=11),
                text_color="gray60",
            ).pack(pady=(0, 4))

        sf = ctk.CTkScrollableFrame(self, height=260)
        sf.pack(fill="both", expand=True, padx=12, pady=4)

        for r in records:
            record_id = r[9]
            is_active = not r[7]
            sev_color = SEVERITY_COLORS.get(r[8], "gray25")

            f = ctk.CTkFrame(sf, fg_color=sev_color, corner_radius=6)
            f.pack(fill="x", pady=3, padx=4)

            # Чекбокс только для активных (если есть on_fix)
            if is_active and self._on_fix:
                var = ctk.BooleanVar(value=False)
                self._cb_vars[record_id] = var
                ctk.CTkCheckBox(
                    f,
                    variable=var,
                    text=f"{r[1]}  →  {r[2]}",
                    text_color="white",
                    font=ctk.CTkFont(size=11),
                    fg_color="#2b579a",
                    hover_color="#3a6abf",
                ).pack(side="left", padx=10, pady=8)
            else:
                ctk.CTkLabel(
                    f,
                    text=f"{r[1]}  →  {r[2]}",
                    anchor="w",
                    font=ctk.CTkFont(size=11),
                    text_color="white",
                ).pack(side="left", padx=10, pady=8)

            status = "✅ Устранено" if r[7] else "⚠ Активен"
            ctk.CTkLabel(f, text=status, anchor="e", text_color="white").pack(side="right", padx=10)

        # Кнопки выбрать/снять все — только если есть активные
        if self._has_active and self._on_fix:
            sel_row = ctk.CTkFrame(self, fg_color="transparent")
            sel_row.pack(pady=(4, 0))
            ctk.CTkButton(
                sel_row,
                text="Выбрать все",
                width=110,
                height=26,
                command=lambda: [v.set(True) for v in self._cb_vars.values()],
            ).pack(side="left", padx=4)
            ctk.CTkButton(
                sel_row,
                text="Снять все",
                width=110,
                height=26,
                fg_color="gray30",
                command=lambda: [v.set(False) for v in self._cb_vars.values()],
            ).pack(side="left", padx=4)

            # ФИО и дата устранения
            ctk.CTkLabel(self, text="ФИО устраняющего:", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 2))
            self._fixer_entry = ctk.CTkEntry(self, placeholder_text="Петров П.П.", width=300, height=34)
            self._fixer_entry.pack(pady=4)

            date_row = ctk.CTkFrame(self, fg_color="transparent")
            date_row.pack(pady=4)
            ctk.CTkLabel(date_row, text="Дата устранения:").pack(side="left", padx=6)
            self._fix_date_var = ctk.StringVar(value=datetime.date.today().strftime("%d.%m.%Y"))
            self._fix_date_entry = ctk.CTkEntry(date_row, textvariable=self._fix_date_var, width=120)
            self._fix_date_entry.pack(side="left", padx=4)
            self._fix_date_entry.bind("<Button-1>", self._pick_date)

        # Кнопки внизу
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=12)
        ctk.CTkButton(btn_row, text="Закрыть", fg_color="gray35", command=self.destroy, width=110).pack(
            side="left", padx=8
        )

        if self._has_active and self._on_fix:
            ctk.CTkButton(
                btn_row,
                text="✅ Устранить",
                fg_color="#2b579a",
                hover_color="#3a6abf",
                height=40,
                width=140,
                font=ctk.CTkFont(weight="bold"),
                command=self._confirm,
            ).pack(side="left", padx=8)
            self.bind("<Return>", lambda e: self._confirm())

    def _pick_date(self, event=None):
        iso = parse_date_input(self._fix_date_var.get())
        InlineDatePicker(
            master=self,
            anchor_widget=self._fix_date_entry,
            date_var=self._fix_date_var,
            initial_iso=iso,
        )

    def _confirm(self):
        fixer = self._fixer_entry.get().strip()
        if not fixer:
            msg.showwarning("Ошибка", "Введите ФИО устраняющего!")
            return
        selected = [rid for rid, v in self._cb_vars.items() if v.get()]
        if not selected:
            msg.showwarning("Ошибка", "Отметьте хотя бы один дефект!")
            return
        iso_fix = parse_date_input(self._fix_date_var.get())
        if not iso_fix:
            msg.showerror("Ошибка", "Неверный формат даты устранения")
            return
        self.destroy()
        self._on_fix(selected, iso_fix, fixer)
