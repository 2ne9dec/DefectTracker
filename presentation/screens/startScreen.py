import customtkinter as ctk

from shared.utils.dateUtils import fmt_date
from app.logger import get_logger

logger = get_logger(__name__)

class StartScreen:
    """
    Главный экран: список листков осмотра.
    Рисует себя внутри переданного parent-окна.
    """

    def __init__(self, parent, sheets: list[tuple], on_create, on_open, on_delete, on_backup=None):
        """
        Args:
            parent:    Окно приложения (DefectApp).
            sheets:    Данные листков из InspectionSheetService.get_all().
            on_create: Callable() — открыть диалог создания.
            on_open:   Callable(sheet_id).
            on_delete: Callable(sheet_id).
        """
        self._backup_callback = on_backup or (lambda: None)
        self._build(parent, sheets, on_create, on_open, on_delete)

    def _build(self, parent, sheets, on_create, on_open, on_delete):
        # Панель инструментов
        tb = ctk.CTkFrame(parent, fg_color="transparent")
        tb.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkButton(
            tb,
            text="➕  Создать листок осмотра",
            fg_color="#2b579a",
            hover_color="#3a6abf",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=on_create,
        ).pack(side="left")

        # Резервная копия справа
        ctk.CTkButton(
            tb,
            text="💾 Резервная копия",
            width=160,
            height=38,
            fg_color="gray35",
            hover_color="gray50",
            command=self._backup_callback,
        ).pack(side="right", padx=4)

        if not sheets:
            ph = ctk.CTkFrame(parent, fg_color="transparent")
            ph.pack(expand=True)
            ctk.CTkLabel(
                ph,
                text="Нет листков осмотра. Нажмите «Создать» для начала работы.",
                text_color="gray60",
                font=ctk.CTkFont(size=14),
            ).pack(pady=40)
            return

        cols = [
            "№",
            "Филиал",
            "Напряжение",
            "Линия",
            "Дата",
            "Создал",
            "Активные",
            "Устранено",
            "Действия",
        ]
        widths = [44, 180, 140, 520, 100, 170, 80, 80, 180]

        outer = ctk.CTkFrame(parent, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        hdr = ctk.CTkFrame(outer, fg_color="#1e3a6b", corner_radius=6)
        hdr.pack(fill="x", padx=0, pady=(0, 2))
        for i, (h, w) in enumerate(zip(cols, widths)):
            anchor = "w" if i in [1, 2, 3, 5] else "center"
            ctk.CTkLabel(
                hdr,
                text=h,
                width=w,
                height=32,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white",
                anchor=anchor,
            ).grid(row=0, column=i, padx=2, pady=3, sticky="ew")

        ROW_H = 42
        available_h = parent.winfo_height() - 200
        need_scroll = len(sheets) * ROW_H > max(available_h, 200)
        if need_scroll:
            scroll = ctk.CTkScrollableFrame(outer, fg_color="transparent")
            scroll.pack(fill="both", expand=True)
            container = scroll
        else:
            container = ctk.CTkFrame(outer, fg_color="transparent")
            container.pack(fill="both", expand=True)

        for idx, sheet in enumerate(sheets, 1):
            sid = sheet[0]
            active = int(sheet[7] or 0)
            archived = int(sheet[8] or 0)
            row_bg = "gray20" if idx % 2 == 0 else "gray18"

            row = ctk.CTkFrame(container, fg_color=row_bg, corner_radius=4)
            row.pack(fill="x", padx=0, pady=1)

            for i in range(len(widths)):
                row.grid_columnconfigure(i, weight=1 if i == 3 else 0)

            line_txt = sheet[3] 
            
            data_cells = [
                (str(idx), widths[0], "center"),
                (sheet[1], widths[1], "w"),
                (sheet[2], widths[2], "w"),
                (line_txt, widths[3], "w"), # Теперь полный текст
                (fmt_date(sheet[4]), widths[4], "center"),
                (sheet[5], widths[5], "w"),
            ]
            for col_i, (txt, w, anc) in enumerate(data_cells):
                ctk.CTkLabel(
                    row,
                    text=txt,
                    width=w,
                    height=ROW_H,
                    anchor=anc,
                    font=ctk.CTkFont(size=13),
                ).grid(row=0, column=col_i, padx=2, sticky="ew")

            ctk.CTkLabel(
                row,
                text=str(active),
                width=widths[6],
                height=ROW_H,
                corner_radius=4,
                fg_color="#e03131" if active > 0 else "gray30",
                text_color="white",
                anchor="center",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=6, padx=2, sticky="ew")

            ctk.CTkLabel(
                row,
                text=str(archived),
                width=widths[7],
                height=ROW_H,
                corner_radius=4,
                fg_color="#2f9e44" if archived > 0 else "gray30",
                text_color="white",
                anchor="center",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=7, padx=2, sticky="ew")

            act = ctk.CTkFrame(row, fg_color="transparent", width=widths[8])
            act.grid(row=0, column=8, padx=4, sticky="ew")
            ctk.CTkButton(
                act,
                text="📂 Открыть",
                width=90,
                height=30,
                fg_color="#2b579a",
                hover_color="#3a6abf",
                command=lambda s=sid: on_open(s),
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                act,
                text="🗑",
                width=36,
                height=30,
                fg_color="#a00",
                hover_color="#c00",
                command=lambda s=sid: on_delete(s),
            ).pack(side="left", padx=2)
