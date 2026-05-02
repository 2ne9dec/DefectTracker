import datetime
import tkinter.messagebox as msg
import customtkinter as ctk

from shared.utils.dateUtils import parse_date_input, fmt_date
from shared.widgets.datePicker import DatePickerDialog
from shared.constants import SEVERITY_COLORS

class FixDefectDialog(ctk.CTkToplevel):
    """
    Диалог отметки дефектов как устранённых.
    После подтверждения вызывает on_confirm(record_ids, date_fixed, inspector_fix).
    """

    def __init__(self, master, pole_num: int, defects_info: list[dict], on_confirm):
        super().__init__(master)
        self.title(f"Устранение дефектов — Опора №{pole_num}")
        self.geometry("600x540")
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._on_confirm = on_confirm
        self._cb_vars: dict[int, ctk.BooleanVar] = {}

        self._build(pole_num, defects_info)

    def _build(self, pole_num: int, defects_info: list[dict]):
        ctk.CTkLabel(
            self, text=f"ОПОРА №{pole_num}", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(12, 4))
        ctk.CTkLabel(self, text="Отметьте устранённые дефекты:").pack(pady=4)

        sf = ctk.CTkScrollableFrame(self, height=240)
        sf.pack(fill="both", expand=True, padx=12, pady=4)

        for d in defects_info:
            var = ctk.BooleanVar(value=False)
            self._cb_vars[d["id"]] = var
            fr = ctk.CTkFrame(
                sf, fg_color=SEVERITY_COLORS.get(d["severity"], "gray25"), corner_radius=5
            )
            fr.pack(fill="x", padx=4, pady=3)
            ctk.CTkCheckBox(
                fr,
                variable=var,
                text=f"{d['element']}  →  {d['defect']}",
                text_color="white",
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w", padx=10, pady=8)

        hr = ctk.CTkFrame(self, fg_color="transparent")
        hr.pack()
        ctk.CTkButton(
            hr,
            text="Выбрать все",
            width=110,
            height=28,
            command=lambda: [v.set(True) for v in self._cb_vars.values()],
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            hr,
            text="Снять все",
            width=110,
            height=28,
            fg_color="gray30",
            command=lambda: [v.set(False) for v in self._cb_vars.values()],
        ).pack(side="left", padx=4)

        ctk.CTkLabel(
            self, text="ФИО устраняющего:", font=ctk.CTkFont(weight="bold")
        ).pack(pady=(10, 2))
        self._fixer_entry = ctk.CTkEntry(
            self, placeholder_text="Петров П.П.", width=300, height=34
        )
        self._fixer_entry.pack(pady=4)

        fix_date_row = ctk.CTkFrame(self, fg_color="transparent")
        fix_date_row.pack(pady=4)
        ctk.CTkLabel(fix_date_row, text="Дата устранения:").pack(side="left", padx=6)
        self._fix_date_var = ctk.StringVar(
            value=datetime.date.today().strftime("%d.%m.%Y")
        )
        ctk.CTkEntry(fix_date_row, textvariable=self._fix_date_var, width=110).pack(
            side="left", padx=4
        )
        ctk.CTkButton(fix_date_row, text="📅", width=32, command=self._pick_date).pack(
            side="left"
        )

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=12)
        ctk.CTkButton(
            btn_row, text="❌ Отмена", fg_color="gray35", command=self.destroy, width=110
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_row,
            text="✅ Сохранить",
            fg_color="#2b579a",
            hover_color="#3a6abf",
            height=40,
            width=140,
            font=ctk.CTkFont(weight="bold"),
            command=self._confirm,
        ).pack(side="left", padx=8)
        self.bind("<Return>", lambda e: self._confirm())

    def _pick_date(self):
        iso = parse_date_input(self._fix_date_var.get())
        r = DatePickerDialog.ask(self, initial_date=iso, title="Дата устранения")
        if r:
            self._fix_date_var.set(fmt_date(r))

    def _confirm(self):
        fixer = self._fixer_entry.get().strip()
        if not fixer:
            msg.showwarning("Ошибка", "Введите ФИО устраняющего!")
            return
        selected = [rid for rid, v in self._cb_vars.items() if v.get()]
        if not selected:
            msg.showwarning("Ошибка", "Выберите хотя бы один дефект!")
            return
        iso_fix = parse_date_input(self._fix_date_var.get())
        if not iso_fix:
            msg.showerror("Ошибка", "Неверный формат даты устранения")
            return
        self.destroy()
        self._on_confirm(selected, iso_fix, fixer)
