import customtkinter as ctk

from shared.constants import SEVERITY_COLORS
from shared.utils.dateUtils import fmt_date

def make_summary(records: list[tuple]) -> str:
    """
    Формирует компактную сводку по дефектам опоры.
    "▸ Изолятор (3 шт.)  ▸ Провод (1 шт.)"
    """
    elem_map: dict[str, list] = {}
    for r in records:
        elem_map.setdefault(r[1], []).append(r[2])
    parts = []
    for elem, defs in elem_map.items():
        e_short = elem[:20] + "…" if len(elem) > 20 else elem
        parts.append(f"▸ {e_short} ({len(defs)} шт.)")
    return "  ".join(parts[:3]) + ("  …" if len(parts) > 3 else "")

def make_fixed_summary(records: list[tuple]) -> str:
    """
    Формирует краткую сводку по устранённым дефектам опоры.
    Показывает только те записи, у которых есть дата устранения (r[5]).
    """
    fixed = [r for r in records if r[5]]
    if not fixed:
        return ""
    elem_map: dict[str, list] = {}
    for r in fixed:
        elem_map.setdefault(r[1], []).append(r[2])
    parts = []
    for elem, defs in elem_map.items():
        e_short = elem[:18] + "…" if len(elem) > 18 else elem
        parts.append(f"✓ {e_short} ({len(defs)} шт.)")
    return "  ".join(parts[:2]) + ("  …" if len(parts) > 2 else "")

class _ContextMenu(ctk.CTkToplevel):
    """
    Всплывающее меню с кнопками «Копировать» и «Удалить».
    Закрывается при клике за пределами или при выборе пункта.
    """

    def __init__(self, parent, x, y, on_copy, on_delete):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="gray20")

        frame = ctk.CTkFrame(self, fg_color="gray25", corner_radius=8, border_width=1, border_color="gray40")
        frame.pack(padx=1, pady=1)

        if on_copy:
            ctk.CTkButton(
                frame,
                text="📋  Копировать опору",
                width=180,
                height=34,
                fg_color="transparent",
                hover_color="gray35",
                text_color="white",
                anchor="w",
                font=ctk.CTkFont(size=12),
                command=lambda: (self._close(), on_copy()),
            ).pack(fill="x", padx=4, pady=(4, 1))

        ctk.CTkButton(
            frame,
            text="🗑  Удалить дефекты",
            width=180,
            height=34,
            fg_color="transparent",
            hover_color="#6b1a1a",
            text_color="#ff6b6b",
            anchor="w",
            font=ctk.CTkFont(size=12),
            command=lambda: (self._close(), on_delete()),
        ).pack(fill="x", padx=4, pady=(1, 4))

        self.geometry(f"+{x}+{y}")
        self.bind("<FocusOut>", lambda e: self._close())
        self.focus_set()
        self.bind("<Escape>", lambda e: self._close())

    def _close(self):
        try:
            self.destroy()
        except Exception:
            pass

class DefectTable:
    """
    Компонент таблицы дефектов с группировкой по опорам.
    Принимает контейнер (CTkScrollableFrame) и рисует в нём строки.

    Колонки (одинаковые для обоих вкладок):
      Опора | Кол-во | Активные дефекты | Дата обн. | Обнаружил |
      Дата устр. | Устранил | Устранённые дефекты | Действия
    """

    def __init__(
        self,
        container: ctk.CTkScrollableFrame,
        records: list[tuple],
        tab: str,
        on_detail,
        on_fix,
        on_copy,
        on_delete,
    ):
        """
        Args:
            container: Скроллируемый фрейм для вставки строк.
            records:   Список кортежей из DefectRepository.fetch_records().
            tab:       "active" или "fixed".
            on_detail: Callable(records, pole_num, on_fix) — клик по ячейке дефектов.
            on_fix:    Callable(ids, pole_num)             — кнопка ✓ Устранить.
            on_copy:   Callable(pole_num)                  — пункт меню 📋.
            on_delete: Callable(ids)                       — пункт меню 🗑.
        """
        self._build(container, records, tab, on_detail, on_fix, on_copy, on_delete)

    def _build(self, container, records, tab, on_detail, on_fix, on_copy, on_delete):
        # ── Конфигурация колонок ─────────────────────────────────────────────
        cols = [
            "Опора",  # 0
            "Кол-во",  # 1
            "Элементы / Дефекты",  # 2  (активные)
            "Дата обн.",  # 3
            "Обнаружил",  # 4
            "Дата устр.",  # 5
            "Устранил",  # 6
            "Устранённые",  # 7  (новая колонка)
            "Действия",  # 8
        ]
        widths = [70, 64, 320, 100, 130, 100, 110, 220, 0]  # 0 = растягивается

        # ── Заголовок ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(container, fg_color="#1e3a6b", corner_radius=6)
        hdr.pack(fill="x", pady=(0, 2))
        for i, (h, w) in enumerate(zip(cols, widths)):
            kw = {"width": w} if w else {}
            ctk.CTkLabel(
                hdr,
                text=h,
                height=30,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white",
                anchor="w" if i in (2, 7) else "center",
                **kw,
            ).grid(row=0, column=i, padx=2, pady=2, sticky="ew")
        hdr.grid_columnconfigure(8, weight=1)

        if not records:
            msg_text = (
                "Нет активных дефектов. Добавьте первый дефект выше."
                if tab == "active"
                else "Устранённых дефектов нет."
            )
            ctk.CTkLabel(container, text=msg_text, font=ctk.CTkFont(size=13), text_color="gray60").pack(pady=30)
            return

        # ── Группировка по опорам ────────────────────────────────────────────
        poles: dict[int, list] = {}
        for r in records:
            poles.setdefault(r[0], []).append(r)

        for pole_num, pole_recs in sorted(poles.items()):
            sev = "low"
            for r in pole_recs:
                if r[8] == "critical":
                    sev = "critical"
                    break
                if r[8] == "medium":
                    sev = "medium"

            bg = SEVERITY_COLORS[sev]
            count = len(pole_recs)
            ids = [r[9] for r in pole_recs]

            # Данные устранения
            fixed_recs = [r for r in pole_recs if r[5]]
            active_recs = [r for r in pole_recs if not r[5]]
            is_any_fixed = bool(fixed_recs)
            is_all_fixed = len(fixed_recs) == count

            date_fixed = max((r[5] for r in fixed_recs), default=None)
            fixer = next((r[6] for r in fixed_recs if r[6]), None)

            # ── Строка ──────────────────────────────────────────────────────
            row_f = ctk.CTkFrame(container, fg_color="gray18", corner_radius=4)
            row_f.pack(fill="x", pady=1)

            # Опора
            ctk.CTkLabel(
                row_f,
                text=str(pole_num),
                width=widths[0],
                height=42,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color=bg,
                text_color="white",
                corner_radius=4,
                anchor="center",
            ).grid(row=0, column=0, padx=2, sticky="ew")

            # Кол-во
            ctk.CTkLabel(
                row_f,
                text=str(count),
                width=widths[1],
                height=42,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="gray25",
                corner_radius=4,
                anchor="center",
            ).grid(row=0, column=1, padx=2, sticky="ew")

            # Активные дефекты (кликабельная ячейка)
            active_summary = make_summary(active_recs) if active_recs else "—  все устранены"
            summary_fg = "gray22" if active_recs else "#1a3a1a"
            summary_fg_hover = "gray30" if active_recs else "#254a25"
            summary_lbl = ctk.CTkLabel(
                row_f,
                text=active_summary,
                width=widths[2],
                height=42,
                fg_color=summary_fg,
                corner_radius=4,
                anchor="w",
                justify="left",
                wraplength=widths[2] - 12,
                font=ctk.CTkFont(size=10),
                cursor="hand2",
            )
            summary_lbl.grid(row=0, column=2, padx=2, sticky="ew")
            summary_lbl.bind(
                "<Button-1>",
                lambda e, recs=pole_recs, pn=pole_num: on_detail(recs, pn, on_fix),
            )
            summary_lbl.bind("<Enter>", lambda e, lbl=summary_lbl, c=summary_fg_hover: lbl.configure(fg_color=c))
            summary_lbl.bind("<Leave>", lambda e, lbl=summary_lbl, c=summary_fg: lbl.configure(fg_color=c))

            # Дата обнаружения
            date_found = min((r[3] for r in pole_recs if r[3]), default="-")
            ctk.CTkLabel(
                row_f,
                text=fmt_date(date_found),
                width=widths[3],
                height=42,
                fg_color="gray25",
                corner_radius=4,
                anchor="center",
            ).grid(row=0, column=3, padx=2, sticky="ew")

            # Обнаружил
            inspector = next((r[4] for r in pole_recs if r[4]), "-")
            ctk.CTkLabel(
                row_f,
                text=inspector,
                width=widths[4],
                height=42,
                fg_color="gray25",
                corner_radius=4,
                anchor="w",
            ).grid(row=0, column=4, padx=2, sticky="ew")

            # Дата устранения
            ctk.CTkLabel(
                row_f,
                text=fmt_date(date_fixed) if date_fixed else "—",
                width=widths[5],
                height=42,
                fg_color="#1a4a2e" if date_fixed else "gray22",
                text_color="#6fcf97" if date_fixed else "gray50",
                corner_radius=4,
                anchor="center",
            ).grid(row=0, column=5, padx=2, sticky="ew")

            # Устранил
            ctk.CTkLabel(
                row_f,
                text=fixer if fixer else "—",
                width=widths[6],
                height=42,
                fg_color="#1a4a2e" if fixer else "gray22",
                text_color="#6fcf97" if fixer else "gray50",
                corner_radius=4,
                anchor="w",
            ).grid(row=0, column=6, padx=2, sticky="ew")

            # ── Действия ──────────────────────────────────────────────────
            act = ctk.CTkFrame(row_f, fg_color="transparent")
            act.grid(row=0, column=8, padx=6, sticky="ew")
            row_f.grid_columnconfigure(8, weight=1)

            # Кнопка «Устранить» — только если есть активные дефекты
            if active_recs and tab == "active":
                active_ids = [r[9] for r in active_recs]
                ctk.CTkButton(
                    act,
                    text="✓ Устранить",
                    width=90,
                    height=34,
                    fg_color="#e67700",
                    hover_color="#b35900",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    command=lambda iids=active_ids, pn=pole_num: on_fix(iids, pn),
                ).pack(side="left", padx=2)

            # Кнопка «⋮» — контекстное меню (копировать / удалить)
            def _show_menu(event, pn=pole_num, iids=ids, has_copy=not is_all_fixed):
                btn = event.widget
                x = btn.winfo_rootx()
                y = btn.winfo_rooty() + btn.winfo_height() + 2
                copy_fn = (lambda p=pn: on_copy(p)) if has_copy else None
                _ContextMenu(
                    btn,
                    x,
                    y,
                    on_copy=copy_fn,
                    on_delete=lambda i=iids: on_delete(i),
                )

            menu_btn = ctk.CTkButton(
                act,
                text="⋮",
                width=34,
                height=34,
                fg_color="gray30",
                hover_color="gray45",
                font=ctk.CTkFont(size=16, weight="bold"),
            )
            menu_btn.pack(side="left", padx=2)
            menu_btn.bind("<Button-1>", _show_menu)
