import datetime
import tkinter.messagebox as msg
import customtkinter as ctk

from shared.utils.dateUtils import fmt_date, parse_date_input
from shared.widgets.datePicker import DatePickerDialog
from presentation.dialogs.createSheetDialog import ScrollableDropdown
from shared.constants import SEVERITY_COLORS, SEVERITY_LABELS
from presentation.components.defectTable import DefectTable
from presentation.components.defectTree import DefectTree
from presentation.components.sheetListRow import DetailDialog
from presentation.dialogs.fixDefectDialog import FixDefectDialog
from presentation.dialogs.copyDefectDialog import CopyDefectDialog
from app.logger import get_logger

logger = get_logger(__name__)

class SheetScreen:
    """
    Экран листка осмотра: панель ввода дефекта + таблица.
    Рисует себя внутри переданного parent-окна.
    """

    def __init__(
        self,
        parent,
        sheet_id: int,
        filial: str,
        voltage: str,
        line: str,
        pole_count: int,
        defect_service,
        ref_service,
        on_export,
    ):
        self._parent = parent
        self._sheet_id = sheet_id
        self._filial = filial
        self._voltage = voltage
        self._line = line
        self._pole_count = pole_count
        self._defect_service = defect_service
        self._ref_service = ref_service
        self._on_export = on_export

        self._defect_id_selected: int | None = None
        self._tab_var = ctk.StringVar(value="active")
        self._search_var = ctk.StringVar()
        self._pole_var = ctk.StringVar()
        self._find_date_var = ctk.StringVar(value=datetime.date.today().strftime("%d.%m.%Y"))

        self._build(parent)

    # ─────────────────────────── ПОСТРОЕНИЕ ЭКРАНА ──────────────────────────

    def _build(self, parent):
        self._build_info_bar(parent)
        self._build_tabs(parent)
        self._build_input_panel(parent)
        self._table_scroll = ctk.CTkScrollableFrame(parent, corner_radius=8)
        self._table_scroll.pack(fill="both", expand=True, padx=16, pady=(4, 12))
        self._refresh_table()

    def _build_info_bar(self, parent):
        info = ctk.CTkFrame(parent, fg_color="#243e6b", corner_radius=0)
        info.pack(fill="x")
        ctk.CTkLabel(
            info,
            text=f"Линия: {self._line}   |   Филиал: {self._filial}   |   {self._voltage} кВ",
            font=ctk.CTkFont(size=13),
            text_color="#a8c4f0",
        ).pack(side="left", padx=16, pady=6)
        ctk.CTkButton(
            info,
            text="📊 Экспорт Excel",
            width=150,
            height=30,
            fg_color="#217346",
            hover_color="#1a5c38",
            command=self._on_export,
        ).pack(side="right", padx=12, pady=6)

    def _build_tabs(self, parent):
        tab_bar = ctk.CTkFrame(parent, fg_color="transparent")
        tab_bar.pack(fill="x", padx=16, pady=(8, 0))

        for label, value in [("⚠ Активные", "active"), ("✅ Устранённые", "fixed")]:
            ctk.CTkRadioButton(
                tab_bar,
                text=label,
                variable=self._tab_var,
                value=value,
                command=self._refresh_table,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(side="left", padx=12)

        self._search_var.trace_add("write", lambda *_: self._refresh_table())
        ctk.CTkEntry(
            tab_bar,
            textvariable=self._search_var,
            placeholder_text="🔍 Поиск по дефекту / элементу…",
            width=260,
            height=32,
        ).pack(side="right", padx=4)

    def _build_input_panel(self, parent):
        inp = ctk.CTkFrame(parent, fg_color="gray17", corner_radius=8)
        inp.pack(fill="x", padx=16, pady=(4, 4))

        # ФИО обнаружившего
        ctk.CTkLabel(inp, text="Обнаружил:").grid(row=0, column=0, padx=6, pady=8, sticky="e")
        self._entry_inspector = ctk.CTkEntry(inp, placeholder_text="Иванов И.И.", width=160)
        self._entry_inspector.grid(row=0, column=1, padx=4, pady=8)

        # Дата обнаружения
        ctk.CTkLabel(inp, text="Дата обн.:").grid(row=0, column=2, padx=6, pady=8, sticky="e")
        self._find_date_entry = ctk.CTkEntry(inp, textvariable=self._find_date_var, width=100)
        self._find_date_entry.grid(row=0, column=3, padx=4, pady=8)
        ctk.CTkButton(inp, text="📅", width=32, command=self._pick_find_date).grid(row=0, column=4, padx=2)

        # № Опоры
        ctk.CTkLabel(inp, text="№ Опоры:").grid(row=0, column=5, padx=6, pady=8, sticky="e")

        pole_values = [str(i) for i in range(1, self._pole_count + 1)] if self._pole_count > 0 else []
        self._dd_pole = ScrollableDropdown(
            inp,
            values=pole_values,
            variable=self._pole_var,
            width=90,
            placeholder="Выберите опору…",
        )
        self._dd_pole.widget.grid(row=0, column=6, padx=4, pady=8)

        # Кнопка выбора дефекта
        ctk.CTkLabel(inp, text="Элемент / Дефект:").grid(row=0, column=7, padx=6, pady=8, sticky="e")
        picker_frame = ctk.CTkFrame(inp, fg_color="transparent")
        picker_frame.grid(row=0, column=8, columnspan=3, padx=4, pady=8, sticky="w")
        self._picker_btn = ctk.CTkButton(
            picker_frame,
            text="Выберите элемент и дефект…",
            width=380,
            height=34,
            fg_color="gray25",
            hover_color="gray35",
            anchor="w",
            font=ctk.CTkFont(size=11),
            command=self._open_defect_tree,
        )
        self._picker_btn.pack(side="left")

        # Кнопка добавить
        ctk.CTkButton(
            inp,
            text="➕  Добавить",
            fg_color="#2b579a",
            hover_color="#3a6abf",
            width=120,
            height=36,
            command=self._add_defect,
        ).grid(row=0, column=11, padx=10, pady=8)

    # ────────────────────────── ДЕЙСТВИЯ ─────────────────────────────────────

    def _pick_find_date(self):
        iso = parse_date_input(self._find_date_var.get())
        result = DatePickerDialog.ask(self._parent, initial_date=iso, title="Дата обнаружения")
        if result:
            self._find_date_var.set(fmt_date(result))

    def _open_defect_tree(self):
        tree = self._ref_service.get_defect_tree()
        DefectTree(
            master=self._parent,
            anchor_widget=self._picker_btn,
            tree=tree,
            on_select=self._on_defect_selected,
        )

    def _on_defect_selected(self, elem_name: str, defect_name: str, defect_id: int):
        self._defect_id_selected = defect_id
        self._picker_btn.configure(text=f"{elem_name}  →  {defect_name}")

    def _add_defect(self):
        pole = self._dd_pole.get()
        inspector = self._entry_inspector.get().strip()
        find_date_iso = parse_date_input(self._find_date_var.get())

        if not all([pole, inspector]):
            msg.showwarning("Ошибка", "Заполните поля: Обнаружил, № Опоры")
            return
        if not find_date_iso:
            msg.showerror("Ошибка", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return
        try:
            pole_int = int(pole)
        except ValueError:
            msg.showerror("Ошибка", "Неверный номер опоры")
            return
        if self._pole_count > 0 and not (1 <= pole_int <= self._pole_count):
            msg.showerror("Ошибка", f"Номер опоры: от 1 до {self._pole_count}")
            return
        if not self._defect_id_selected:
            msg.showerror("Ошибка", "Выберите дефект из дерева (кнопка «Элемент / Дефект»)")
            return

        self._defect_service.add(self._sheet_id, pole_int, self._defect_id_selected, find_date_iso, inspector)
        self._defect_id_selected = None
        self._picker_btn.configure(text="Выберите элемент и дефект…")
        self._refresh_table()

    def _refresh_table(self):
        for w in self._table_scroll.winfo_children():
            w.destroy()

        tab = self._tab_var.get()
        is_fixed = 1 if tab == "fixed" else 0
        search = self._search_var.get().strip().lower()
        records = self._defect_service.fetch_records(self._sheet_id, is_fixed, search)

        DefectTable(
            container=self._table_scroll,
            records=records,
            tab=tab,
            on_detail=self._detail_dialog,
            on_fix=self._fix_dialog,
            on_copy=self._copy_pole_dialog,
            on_delete=self._delete_defects,
        )

    def _detail_dialog(self, records: list, pole_num: int):
        DetailDialog(self._parent, pole_num, records)

    def _fix_dialog(self, record_ids: list[int], pole_num: int):
        defects_info = self._defect_service.get_defects_info(record_ids)
        FixDefectDialog(
            master=self._parent,
            pole_num=pole_num,
            defects_info=defects_info,
            on_confirm=lambda ids, date_f, insp: self._on_fix_confirmed(ids, date_f, insp),
        )

    def _on_fix_confirmed(self, ids: list[int], date_fixed: str, inspector_fix: str):
        self._defect_service.fix_many(ids, date_fixed, inspector_fix)
        self._refresh_table()

    def _copy_pole_dialog(self, source_pole: int):
        src = self._defect_service._repo.get_active_by_pole(self._sheet_id, source_pole)
        if not src:
            msg.showinfo(
                "Нет дефектов",
                f"У опоры №{source_pole} нет активных дефектов для копирования.",
            )
            return
        default_inspector = src[0][1] or ""

        def on_confirm(targets: list[int], inspector: str):
            try:
                count = self._defect_service.copy_pole(
                    self._sheet_id, source_pole, targets, inspector, self._pole_count
                )
                msg.showinfo(
                    "Готово",
                    f"Дефекты скопированы на {len(targets)} опор(у): " f"{', '.join(str(t) for t in targets)}",
                )
                self._refresh_table()
            except ValueError as e:
                msg.showerror("Ошибка", str(e))

        CopyDefectDialog(
            master=self._parent,
            source_pole=source_pole,
            defect_count=len(src),
            default_inspector=default_inspector,
            on_confirm=on_confirm,
        )

    def _delete_defects(self, ids: list[int]):
        if ids and msg.askyesno("Подтверждение", "Удалить выбранные дефекты?"):
            self._defect_service.delete_many(ids)
            self._refresh_table()
