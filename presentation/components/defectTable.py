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
        # Конфигурация колонок
        if tab == "active":
            cols = [
                "Опора",
                "Кол-во",
                "Элементы / Дефекты",
                "Дата обн.",
                "Обнаружил",
                "Статус",
                "Действия",
            ]
            widths = [70, 64, 420, 100, 150, 110, 170]
        else:
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
            widths = [70, 64, 340, 100, 130, 100, 130, 130]

        # Заголовок
        hdr = ctk.CTkFrame(container, fg_color="#1e3a6b", corner_radius=6)
        hdr.pack(fill="x", pady=(0, 2))
        for i, (h, w) in enumerate(zip(cols, widths)):
            ctk.CTkLabel(
                hdr,
                text=h,
                width=w,
                height=30,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white",
                anchor="w" if i == 2 else "center",
            ).grid(row=0, column=i, padx=2, pady=2, sticky="ew")

        if not records:
            msg = (
                "Нет активных дефектов. Добавьте первый дефект выше."
                if tab == "active"
                else "Устранённых дефектов нет."
            )
            ctk.CTkLabel(
                container, text=msg, font=ctk.CTkFont(size=13), text_color="gray60"
            ).pack(pady=30)
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
            ctk.CTkLabel(
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
            ).grid(row=0, column=2, padx=2, sticky="ew")

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

            col_offset = 5
            if tab == "fixed":
                date_fixed = max((r[5] for r in pole_recs if r[5]), default="-")
                ctk.CTkLabel(
                    row_f,
                    text=fmt_date(date_fixed),
                    width=widths[5],
                    height=42,
                    fg_color="gray25",
                    corner_radius=4,
                    anchor="center",
                ).grid(row=0, column=5, padx=2, sticky="ew")
                fixer = next((r[6] for r in pole_recs if r[6]), "-")
                ctk.CTkLabel(
                    row_f,
                    text=fixer,
                    width=widths[6],
                    height=42,
                    fg_color="gray25",
                    corner_radius=4,
                    anchor="w",
                ).grid(row=0, column=6, padx=2, sticky="ew")
                col_offset = 7
            else:
                ctk.CTkLabel(
                    row_f,
                    text="⚠  Не устранено",
                    width=widths[5],
                    height=42,
                    fg_color="#8b4800",
                    text_color="white",
                    corner_radius=4,
                    anchor="center",
                ).grid(row=0, column=5, padx=2, sticky="ew")
                col_offset = 6

            act = ctk.CTkFrame(row_f, fg_color="transparent")
            act.grid(row=0, column=col_offset, padx=6, sticky="ew")

            ctk.CTkButton(
                act,
                text="🔍",
                width=38,
                height=34,
                fg_color="gray35",
                hover_color="gray50",
                command=lambda recs=pole_recs, pn=pole_num: on_detail(recs, pn),
            ).pack(side="left", padx=2)

            if tab == "active":
                ctk.CTkButton(
                    act,
                    text="✓ Устранить",
                    width=90,
                    height=34,
                    fg_color="#e67700",
                    hover_color="#b35900",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    command=lambda iids=ids, pn=pole_num: on_fix(iids, pn),
                ).pack(side="left", padx=2)
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
