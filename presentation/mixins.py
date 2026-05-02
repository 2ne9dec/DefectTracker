import customtkinter as ctk

class AppMixins:
    """
    Вспомогательные методы интерфейса, общие для всех экранов.
    Подмешивается к DefectApp через множественное наследование.
    """

    def _clear(self):
        """Удаляет все дочерние виджеты окна перед переключением экрана."""
        for w in self.winfo_children():
            w.destroy()

    def _header(self, parent, text: str, with_back: bool = False) -> ctk.CTkFrame:
        """
        Создаёт стандартную шапку экрана.

        Args:
            parent:    Родительский виджет.
            text:      Заголовок.
            with_back: Показывать кнопку «← Назад».

        Returns:
            Созданный фрейм шапки.
        """
        bar = ctk.CTkFrame(parent, fg_color="#1a3a6b", corner_radius=0)
        bar.pack(fill="x")
        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=8)
        if with_back:
            ctk.CTkButton(
                inner,
                text="← Назад",
                width=90,
                height=32,
                fg_color="#2b579a",
                hover_color="#3a6abf",
                command=self._show_start,
            ).pack(side="left")
        ctk.CTkLabel(
            inner,
            text=text,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="white",
        ).pack(side="left", padx=12)
        return bar

    def _maximize(self):
        """Разворачивает окно на весь экран (кроссплатформенно)."""
        import sys

        try:
            if sys.platform == "win32":
                self.wm_state("zoomed")
            else:
                self.attributes("-zoomed", True)
        except Exception:
            try:
                w = self.winfo_screenwidth()
                h = self.winfo_screenheight()
                self.geometry(f"{w}x{h}+0+0")
            except Exception:
                pass
