import tkinter.messagebox as msg
import customtkinter as ctk

class CopyDefectDialog(ctk.CTkToplevel):
    """
    Диалог копирования дефектов опоры на другие опоры.
    После подтверждения вызывает on_confirm(target_poles, inspector).
    """

    def __init__(
        self,
        master,
        source_pole: int,
        defect_count: int,
        default_inspector: str,
        on_confirm,
    ):
        super().__init__(master)
        self.title(f"Копировать дефекты опоры №{source_pole}")
        self.geometry("400x300")
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._on_confirm = on_confirm
        self._build(source_pole, defect_count, default_inspector)

    def _build(self, source_pole: int, defect_count: int, default_inspector: str):
        ctk.CTkLabel(
            self,
            text=f"Копировать {defect_count} дефект(ов) опоры №{source_pole}",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=12)
        ctk.CTkLabel(self, text="Целевые номера опор (через запятую):").pack(pady=4)

        self._entry = ctk.CTkEntry(
            self, placeholder_text="например: 12, 13, 15", width=280
        )
        self._entry.pack(pady=6)

        ctk.CTkLabel(self, text="Обнаружил:", anchor="w").pack(pady=(8, 2))
        self._inspector_e = ctk.CTkEntry(self, placeholder_text="Иванов И.И.", width=280)
        self._inspector_e.insert(0, default_inspector)
        self._inspector_e.pack(pady=4)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=12)
        ctk.CTkButton(
            btn_row, text="Отмена", fg_color="gray35", command=self.destroy, width=100
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_row,
            text="✅ Копировать",
            fg_color="#2b579a",
            command=self._confirm,
            width=120,
        ).pack(side="left", padx=6)
        self.bind("<Return>", lambda e: self._confirm())

    def _confirm(self):
        raw = self._entry.get().strip()
        inspector = self._inspector_e.get().strip()
        if not raw or not inspector:
            msg.showwarning("Ошибка", "Заполните все поля!")
            return
        targets = []
        for part in raw.split(","):
            p = part.strip()
            if p.isdigit():
                targets.append(int(p))
            else:
                msg.showerror("Ошибка", f"Некорректный номер опоры: '{p}'")
                return
        self.destroy()
        self._on_confirm(targets, inspector)
