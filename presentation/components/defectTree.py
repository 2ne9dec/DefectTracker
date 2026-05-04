import tkinter as tk

class DefectTree:
    """
    Всплывающее дерево выбора дефекта.
    - Левая панель: элементы с индикатором скролла снизу.
    - Правая панель: дефекты рядом с элементом.
    - Закрытие: ESC, клик вне, переключение приложения.
    """

    ELEM_W = 260
    DEF_W = 370
    ROW_H = 34
    SEP_W = 3
    FONT_SZ = 12
    MAX_VIS = 18
    HINT_H = 24  # высота полоски-подсказки

    SEV_BG = {"critical": "#5c1a1a", "medium": "#4d3000", "low": "#1a3d1a"}
    SEV_FG = {"critical": "#ff8080", "medium": "#ffb347", "low": "#80e080"}

    def __init__(self, master, anchor_widget, tree: dict, on_select):
        self._tree = tree
        self._on_select = on_select
        self._master = master
        self._popup = None
        self._sub_popup = None
        self._closed = False
        self._esc_id = None
        self._click_id = None
        self._focus_id = None
        self._root = None
        self._show(anchor_widget)

    def _close_all(self, *_):
        if self._closed:
            return
        self._closed = True
        self._unbind()
        try:
            self._sub_popup.destroy()
        except Exception:
            pass
        try:
            self._popup.destroy()
        except Exception:
            pass

    def _unbind(self):
        if not self._root:
            return
        for attr, event in [("_esc_id", "<KeyPress>"), ("_click_id", "<ButtonPress>"), ("_focus_id", "<FocusOut>")]:
            bid = getattr(self, attr, None)
            if bid:
                try:
                    self._root.unbind(event, bid)
                except Exception:
                    pass

    def _is_inside(self, win, rx, ry):
        try:
            wx, wy = win.winfo_rootx(), win.winfo_rooty()
            ww, wh = win.winfo_width(), win.winfo_height()
            return wx <= rx <= wx + ww and wy <= ry <= wy + wh
        except Exception:
            return False

    def _on_show(self):
        self._root = self._master.winfo_toplevel()

        def on_key(e):
            if e.keysym == "Escape":
                self._close_all()

        def on_click(e):
            if self._closed:
                return
            rx, ry = e.x_root, e.y_root
            if not self._is_inside(self._popup, rx, ry) and not (
                self._sub_popup and self._is_inside(self._sub_popup, rx, ry)
            ):
                self._close_all()

        def on_focus_out(e):
            if e.widget == self._root:
                self._close_all()

        self._esc_id = self._root.bind("<KeyPress>", on_key, add="+")
        self._click_id = self._root.bind("<ButtonPress>", on_click, add="+")
        self._focus_id = self._root.bind("<FocusOut>", on_focus_out, add="+")

    def _show(self, anchor_widget):
        anchor_widget.update_idletasks()
        bx = anchor_widget.winfo_rootx()
        by = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 4

        items = sorted(self._tree.items(), key=lambda x: x[1]["name"])
        n = len(items)
        screen_h = anchor_widget.winfo_screenheight()
        max_h = screen_h - by - 60

        vis_rows = min(n, self.MAX_VIS)
        need_scroll = n > vis_rows
        # Если скролл нужен — оставляем место для полоски снизу
        canvas_h = min(vis_rows * self.ROW_H, max_h - (self.HINT_H if need_scroll else 0))
        popup_h = canvas_h + (self.HINT_H if need_scroll else 0)

        popup = tk.Toplevel(self._master)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg="#1a2840")
        self._popup = popup

        # Строим layout: canvas сверху, hint снизу
        canvas = tk.Canvas(
            popup,
            width=self.ELEM_W,
            height=canvas_h,
            bg="#252525",
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(side="top", fill="both", expand=True)

        # Полоски-стрелки сверху и снизу — показывают куда можно скролить
        if need_scroll:
            hint_top = tk.Frame(popup, bg="#1a2840", height=self.HINT_H)
            hint_top.pack_propagate(False)
            hint_top_lbl = tk.Label(
                hint_top,
                text="▲",
                bg="#1a2840",
                fg="#6a9fd8",
                font=("Segoe UI", 8),
            )
            hint_top_lbl.pack(expand=True)

            hint_bot = tk.Frame(popup, bg="#1a2840", height=self.HINT_H)
            hint_bot.pack(side="bottom", fill="x")
            hint_bot.pack_propagate(False)
            hint_bot_lbl = tk.Label(
                hint_bot,
                text=f"▼",
                bg="#1a2840",
                fg="#6a9fd8",
                font=("Segoe UI", 8),
            )
            hint_bot_lbl.pack(expand=True)

            # Изначально верхняя стрелка скрыта (мы вверху)
            hint_top.pack_forget()

            sb = tk.Scrollbar(popup, orient="vertical", command=canvas.yview)

            def _update_hints(*_):
                try:
                    top, bot = canvas.yview()
                    # Верхняя стрелка: появляется как только прокрутили хоть немного
                    if top > 0.001:
                        hint_top.pack(side="top", fill="x", before=canvas)
                    else:
                        hint_top.pack_forget()
                    # Нижняя стрелка: исчезает только когда докрутили до самого конца
                    if bot < 1.0:
                        hint_bot.pack(side="bottom", fill="x")
                    else:
                        hint_bot.pack_forget()
                except Exception:
                    pass

            canvas.configure(yscrollcommand=lambda *a: (sb.set(*a), _update_hints()))

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            if need_scroll:
                popup.after(10, lambda: canvas.event_generate("<<ScrollUpdate>>"))

        canvas.bind("<MouseWheel>", _on_wheel)

        inner = tk.Frame(canvas, bg="#252525")
        canvas_win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize_inner(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_win, width=self.ELEM_W)

        inner.bind("<Configure>", _resize_inner)

        # --- Sub-popup с дефектами ---
        def show_defects(eid: int, elem_label: tk.Label):
            if self._closed:
                return
            if self._sub_popup:
                try:
                    self._sub_popup.destroy()
                except Exception:
                    pass
                self._sub_popup = None

            defects = self._tree[eid]["defects"]
            if not defects:
                return

            lbl_y = elem_label.winfo_rooty()
            left_x = popup.winfo_rootx() + popup.winfo_width() + 4

            sub = tk.Toplevel(self._master)
            sub.overrideredirect(True)
            sub.attributes("-topmost", True)
            sub.configure(bg="#1e1e1e")
            self._sub_popup = sub

            sep = tk.Frame(sub, bg="#2b579a", width=self.SEP_W)
            sep.pack(side="left", fill="y")
            def_frame = tk.Frame(sub, bg="#1a1a1a")
            def_frame.pack(side="left", fill="both", expand=True)

            for did, dname, sev in defects:
                bg = self.SEV_BG.get(sev, "#2a2a2a")
                fg = self.SEV_FG.get(sev, "#cccccc")
                short = dname if len(dname) <= 44 else dname[:43] + "…"
                lbl = tk.Label(
                    def_frame,
                    text=f"  {short}",
                    bg=bg,
                    fg=fg,
                    font=("Segoe UI", self.FONT_SZ),
                    anchor="w",
                    width=self.DEF_W // 7,
                    cursor="hand2",
                )
                lbl.pack(fill="x", padx=0, pady=1, ipady=5)
                lbl.bind("<MouseWheel>", _on_wheel)

                def on_click(event, _did=did, _dname=dname, _eid=eid):
                    elem_name = self._tree[_eid]["name"]
                    self._closed = True
                    self._unbind()
                    try:
                        sub.destroy()
                    except Exception:
                        pass
                    try:
                        popup.destroy()
                    except Exception:
                        pass
                    self._on_select(elem_name, _dname, _did)

                def on_enter(e, w=lbl):
                    w.configure(bg="#3a5a8a", fg="white")

                def on_leave(e, w=lbl, b=bg, f=fg):
                    w.configure(bg=b, fg=f)

                lbl.bind("<Button-1>", on_click)
                lbl.bind("<Enter>", on_enter)
                lbl.bind("<Leave>", on_leave)

            sub.update_idletasks()
            sub_h = sub.winfo_reqheight()
            screen_h2 = sub.winfo_screenheight()
            if lbl_y + sub_h > screen_h2 - 40:
                lbl_y = screen_h2 - sub_h - 40
            lbl_y = max(lbl_y, 0)
            sub.geometry(f"{self.DEF_W + self.SEP_W}x{sub_h}+{left_x}+{lbl_y}")

        # --- Строки элементов ---
        _active_lbl = [None]

        for eid, edata in items:
            ename = edata["name"]
            short = ename if len(ename) <= 30 else ename[:29] + "…"
            lbl = tk.Label(
                inner,
                text=f"  {short}  ▶",
                bg="#252525",
                fg="#d0d0d0",
                font=("Segoe UI", self.FONT_SZ),
                anchor="w",
                cursor="hand2",
            )
            lbl.pack(fill="x", padx=0, pady=0, ipady=5)
            lbl.bind("<MouseWheel>", _on_wheel)

            def on_enter(e, _eid=eid, w=lbl):
                if _active_lbl[0] and _active_lbl[0] is not w:
                    _active_lbl[0].configure(bg="#252525", fg="#d0d0d0")
                _active_lbl[0] = w
                w.configure(bg="#2b579a", fg="white")
                show_defects(_eid, w)

            lbl.bind("<Enter>", on_enter)

        popup.update_idletasks()
        popup.geometry(f"{self.ELEM_W}x{popup_h}+{bx}+{by}")

        popup.after(300, self._on_show)
