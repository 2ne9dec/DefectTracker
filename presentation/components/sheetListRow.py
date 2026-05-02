import customtkinter as ctk

from shared.constants import SEVERITY_COLORS, SEVERITY_LABELS
from shared.utils.dateUtils import fmt_date

class DetailDialog(ctk.CTkToplevel):
    """Модальное окно с подробным списком всех дефектов одной опоры."""

    def __init__(self, master, pole_num: int, records: list[tuple]):
        super().__init__(master)
        self.title(f"Опора №{pole_num} — все дефекты")
        self.geometry("640x480")
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        ctk.CTkLabel(
            self, text=f"Опора №{pole_num}", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=10)

        sf = ctk.CTkScrollableFrame(self)
        sf.pack(fill="both", expand=True, padx=12, pady=4)

        for r in records:
            sev_color = SEVERITY_COLORS.get(r[8], "gray25")
            f = ctk.CTkFrame(sf, fg_color=sev_color, corner_radius=6)
            f.pack(fill="x", pady=3, padx=4)
            ctk.CTkLabel(
                f,
                text=f"[{SEVERITY_LABELS.get(r[8], '?')}]  {r[1]}  →  {r[2]}",
                anchor="w",
                font=ctk.CTkFont(size=11),
                text_color="white",
            ).pack(side="left", padx=10, pady=6)
            status = "✅ Устранено" if r[7] else "⚠ Активен"
            ctk.CTkLabel(f, text=status, anchor="e", text_color="white").pack(
                side="right", padx=10
            )

        ctk.CTkButton(self, text="Закрыть", command=self.destroy).pack(pady=10)
