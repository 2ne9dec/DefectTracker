import tkinter as tk

class ScrollableList:
    def __init__(
        self,
        parent,
        *,
        width: int = 260,
        row_height: int = 34,
        max_visible: int | None = None,
        bg: str = "#252525",
        hint_bg: str = "#1a2840",
        hint_fg: str = "#6a9fd8",
        hint_h: int = 22,
    ):
        self._row_height = row_height
        self._max_visible = max_visible
        self._hint_bg = hint_bg
        self._hint_fg = hint_fg
        self._hint_h = hint_h
        self._width = width
        self._bg = bg
        self._row_count = 0
        self._need_scroll = False

        # Внешний контейнер
        self.frame = tk.Frame(parent, bg=hint_bg)

        # --- ВЕРХНЯЯ СТРЕЛКА ---
        self._hint_top = tk.Frame(self.frame, bg=hint_bg, height=hint_h)
        self._hint_top.pack_propagate(False)
        tk.Label(self._hint_top, text="▲", bg=hint_bg, fg=hint_fg, font=("Segoe UI", 9)).pack(expand=True)

        # --- CANVAS ---
        self._canvas = tk.Canvas(
            self.frame,
            width=width,
            bg=bg,
            highlightthickness=0,
            bd=0,
        )
        # Canvas занимает всё доступное место
        self._canvas.pack(side="top", fill="both", expand=True)

        # --- НИЖНЯЯ СТРЕЛКА ---
        self._hint_bot = tk.Frame(self.frame, bg=hint_bg, height=hint_h)
        self._hint_bot.pack_propagate(False)
        tk.Label(self._hint_bot, text="▼", bg=hint_bg, fg=hint_fg, font=("Segoe UI", 9)).pack(expand=True)
        # Аналогично, пока не пакуем

        # Scrollbar (невидимый)
        self._sb = tk.Scrollbar(self.frame, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._on_yscroll)

        # Внутренний фрейм
        self.inner = tk.Frame(self._canvas, bg=bg)
        self._win_id = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_configure)

        # Прокрутка колесом
        self._canvas.bind("<MouseWheel>", self._on_wheel)

    # ------------------------------------------------------------------ #
    #  Публичный API
    # ------------------------------------------------------------------ #

    def add_row(self, widget_factory):
        w = widget_factory(self.inner)
        if w is not None:
            self._bind_wheel(w)
        self._row_count += 1
        return w

    def compute_height(self) -> int:
        n = self._row_count
        vis = n if self._max_visible is None else min(n, self._max_visible)
        self._need_scroll = n > vis

        canvas_h = vis * self._row_height
        total_h = canvas_h + (2 * self._hint_h if self._need_scroll else 0)

        self._canvas.configure(height=canvas_h)

        if self._need_scroll:
            self._hint_top.pack_forget()
            self._hint_bot.pack(side="bottom", fill="x")
        else:
            self._hint_top.pack_forget()
            self._hint_bot.pack_forget()

        return total_h

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def place(self, **kwargs):
        self.frame.place(**kwargs)

    def bind_all_children(self, sequence, func):
        self._canvas.bind(sequence, func)
        for w in self.inner.winfo_children():
            try:
                w.bind(sequence, func)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  Внутренние методы
    # ------------------------------------------------------------------ #

    def _on_inner_configure(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._canvas.itemconfig(self._win_id, width=self._width)
        self.frame.after_idle(self._update_hints)

    def _on_yscroll(self, *args):
        self._sb.set(*args)
        self._update_hints()

    def _update_hints(self):
        if not self._need_scroll:
            return

        try:
            top, bot = self._canvas.yview()

            # --- ЛОГИКА ДЛЯ ВЕРХА (TOP) ---
            if top > 0.001:
                self._hint_top.pack(side="top", fill="x", before=self._canvas)
            else:
                self._hint_top.pack_forget()

            # --- ЛОГИКА ДЛЯ НИЗА (BOT) ---
            if round(bot, 4) < 0.999:
                self._hint_bot.pack(side="bottom", fill="x")
            else:
                self._hint_bot.pack_forget()

        except Exception:
            pass

    def _on_wheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.frame.after(50, self._update_hints)

    def _bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_wheel)
        for child in widget.winfo_children():
            self._bind_wheel(child)
