import customtkinter as ctk

from shared.constants import SEVERITY_COLORS, SEVERITY_LABELS
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

class DefectTable:
    """
    Компонент таблицы дефектов с группировкой по опорам.
    Принимает контейнер (CTkScrollableFrame) и рисует в нём строки.
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
            on_detail: Callable(records, pole_num) — кнопка 🔍.
            on_fix:    Callable(ids, pole_num)     — кнопка ✓ Устранить.
            on_copy:   Callable(pole_num)           — кнопка 📋.
            on_delete: Callable(ids)                — кнопка 🗑.
        """
        self._build(container, records, tab, on_detail, on_fix, on_copy, on_delete)

    def _build(self, container, records, tab, on_detail, on_fix, on_copy, on_delete):
        # Единая конфигурация колонок: всегда показываем дату устр. и кто устранил
        cols = [
            "Опора",
            "Кол-во",
            "Элементы / Дефекты",
            "Дата обн.",
            "Обнаружил",
            "Дата устр.",
            "Устранил",
            "Действия",
        ]
        widths = [70, 64, 520, 100, 130, 100, 130, 0]  # 0 = actions stretches

        # Заголовок
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
                anchor="w" if i == 2 else "center",
                **kw,
            ).grid(row=0, column=i, padx=2, pady=2, sticky="ew")
        hdr.grid_columnconfigure(7, weight=1)  # Действия растягиваются

        if not records:
            msg = (
                "Нет активных дефектов. Добавьте первый дефект выше."
                if tab == "active"
                else "Устранённых дефектов нет."
            )
            ctk.CTkLabel(container, text=msg, font=ctk.CTkFont(size=13), text_color="gray60").pack(pady=30)
            return

        # Группировка по опорам
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

            row_f = ctk.CTkFrame(container, fg_color="gray18", corner_radius=4)
            row_f.pack(fill="x", pady=1)

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

            summary = make_summary(pole_recs)
            summary_lbl = ctk.CTkLabel(
                row_f,
                text=summary,
                width=widths[2],
                height=42,
                fg_color="gray22",
                corner_radius=4,
                anchor="w",
                justify="left",
                wraplength=widths[2] - 12,
                font=ctk.CTkFont(size=10),
                cursor="hand2",
            )
            summary_lbl.grid(row=0, column=2, padx=2, sticky="ew")
            summary_lbl.bind("<Button-1>", lambda e, recs=pole_recs, pn=pole_num: on_detail(recs, pn, on_fix))
            summary_lbl.bind("<Enter>", lambda e, lbl=summary_lbl: lbl.configure(fg_color="gray30"))
            summary_lbl.bind("<Leave>", lambda e, lbl=summary_lbl: lbl.configure(fg_color="gray22"))

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

            # Колонки устранения — всегда отображаем
            is_fixed_row = any(r[5] for r in pole_recs)
            date_fixed = max((r[5] for r in pole_recs if r[5]), default=None)
            fixer = next((r[6] for r in pole_recs if r[6]), None)

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

            col_offset = 7

            act = ctk.CTkFrame(row_f, fg_color="transparent")
            act.grid(row=0, column=col_offset, padx=6, sticky="ew")
            row_f.grid_columnconfigure(col_offset, weight=1)

            if not is_fixed_row:
                ctk.CTkButton(
                    act,
                    text="📋",
                    width=38,
                    height=34,
                    fg_color="gray35",
                    hover_color="gray50",
                    command=lambda pn=pole_num: on_copy(pn),
                ).pack(side="left", padx=2)

            ctk.CTkButton(
                act,
                text="🗑",
                width=38,
                height=34,
                fg_color="#900",
                hover_color="#c00",
                command=lambda iids=ids: on_delete(iids),
            ).pack(side="left", padx=2)
