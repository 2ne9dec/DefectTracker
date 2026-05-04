import tkinter as tk
from shared.widgets.scrollableList import ScrollableList
from shared import popupManager

class DefectTree:
    """
    Всплывающее дерево выбора дефекта.
    Исправлено: корректное закрытие по ESC, клику вне и Alt+Tab
    даже при активном под-меню дефектов.
    """

    ELEM_W = 260
    DEF_W = 370
    ROW_H = 34
    SEP_W = 3
    FONT_SZ = 12
    MAX_VIS = 18

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
        self._unmap_id = None

        self._root = None
        self._show(anchor_widget)

    def _close_all(self, *_):
        if self._closed:
            return
        self._closed = True
        self._unbind()
        popupManager.unregister(self)

        for win in [self._sub_popup, self._popup]:
            if win:
                try:
                    win.destroy()
                except Exception:
                    pass

    def _unbind(self):
        if not self._root:
            return
        bindings = [
            (self._esc_id, "<KeyPress>"),
            (self._click_id, "<ButtonPress>"),
            (self._focus_id, "<FocusOut>"),
            (self._unmap_id, "<Unmap>"),
        ]
        for bid, event in bindings:
            if bid:
                try:
                    self._root.unbind(event, bid)
                except Exception:
                    pass

    def _is_mouse_inside(self):
        """
        Проверяет, находится ли мышь внутри ЛЮБОГО из наших окон.
        Каждое окно проверяется отдельно — иначе пространство между
        popup и sub_popup ошибочно считалось бы «внутри».
        """
        try:
            mx = self._root.winfo_pointerx()
            my = self._root.winfo_pointery()
        except Exception:
            return False

        for win in [self._popup, self._sub_popup]:
            if win and win.winfo_exists():
                try:
                    x = win.winfo_rootx()
                    y = win.winfo_rooty()
                    w = win.winfo_width()
                    h = win.winfo_height()
                    if x <= mx <= x + w and y <= my <= y + h:
                        return True
                except Exception:
                    continue

        return False

    def _on_show(self):
        self._root = self._master.winfo_toplevel()

        def on_key(e):
            if e.keysym == "Escape":
                self._close_all()

        def on_click(e):
            if self._closed:
                return

            if not self._is_mouse_inside():
                self._close_all()

        def on_focus_out(e):
            if self._closed:
                return

            self._root.after(150, self._check_focus_lost_alt_tab)

        def on_unmap(e):
            if e.widget == self._root:
                self._root.after(50, self._check_focus_lost_alt_tab)

        self._esc_id = self._root.bind("<KeyPress>", on_key, add="+")
        self._click_id = self._root.bind("<ButtonPress>", on_click, add="+")
        self._focus_id = self._root.bind("<FocusOut>", on_focus_out, add="+")
        self._unmap_id = self._root.bind("<Unmap>", on_unmap, add="+")
        self._bind_click_to_popups(on_click)

    def _bind_recursive(self, widget, sequence, func):
        """Рекурсивно привязывает обработчик к виджету и всем его потомкам."""
        try:
            widget.bind(sequence, func, add="+")
        except Exception:
            pass
        for child in widget.winfo_children():
            self._bind_recursive(child, sequence, func)

    def _bind_click_to_popups(self, on_click):
        """
        Привязывает обработчик клика к popup-окнам, чтобы клики на пустые
        места внутри них (но не на элементы списка) тоже закрывали меню.
        Вызывается после создания _popup; для _sub_popup вызывается при его создании.
        """
        for win in [self._popup, self._sub_popup]:
            if win and win.winfo_exists():
                try:
                    win.bind("<ButtonPress>", on_click, add="+")
                except Exception:
                    pass

    def _check_focus_lost(self):
        """
        Проверяет, потеряли ли мы фокус окончательно.
        Используется для кликов вне области.
        """
        if self._closed:
            return

        if self._is_mouse_inside():
            return

        focused = self._root.focus_get()

        if focused:
            parent_win = focused.winfo_toplevel()
            if parent_win == self._popup or parent_win == self._sub_popup:
                return

        self._close_all()

    def _check_focus_lost_alt_tab(self):
        """
        Проверяет потерю фокуса при Alt+Tab / переключении окон.
        В отличие от _check_focus_lost НЕ проверяет позицию мыши —
        при Alt+Tab фокус уходит, но курсор может оставаться над нашим окном.
        """
        if self._closed:
            return

        try:
            focused = self._root.focus_get()
        except Exception:
            self._close_all()
            return

        if focused is None:
            self._close_all()
            return

        try:
            focused_top = focused.winfo_toplevel()
        except Exception:
            self._close_all()
            return

        if focused_top != self._root and focused_top != self._popup and focused_top != self._sub_popup:
            self._close_all()

    def _poll_focus(self):
        """
        Периодически проверяет, не потеряло ли приложение фокус (Alt+Tab и т.п.).
        Работает даже когда overrideredirect-окна «съедают» события FocusOut.
        """
        if self._closed:
            return

        if not self._root:
            self._popup.after(100, self._poll_focus)
            return

        try:
            focused = self._root.focus_get()
            if focused is None:
                self._close_all()
                return

            focused_top = focused.winfo_toplevel()
            if focused_top != self._root and focused_top != self._popup and focused_top != self._sub_popup:
                self._close_all()
                return
        except Exception:
            self._close_all()
            return

        try:
            self._popup.after(150, self._poll_focus)
        except Exception:
            pass

    def _show(self, anchor_widget):
        anchor_widget.update_idletasks()
        bx = anchor_widget.winfo_rootx()
        by = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 4

        items = sorted(self._tree.items(), key=lambda x: x[1]["name"])
        n = len(items)
        screen_h = anchor_widget.winfo_screenheight()
        max_h = screen_h - by - 60

        max_vis = min(self.MAX_VIS, max_h // self.ROW_H)

        popup = tk.Toplevel(self._master)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg="#1a2840")
        self._popup = popup
        popupManager.register(self)

        sl = ScrollableList(
            popup,
            width=self.ELEM_W,
            row_height=self.ROW_H,
            max_visible=max_vis,
            bg="#252525",
        )

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
            left_x = popup.winfo_rootx() + popup.winfo_width()

            sub = tk.Toplevel(self._master)
            sub.overrideredirect(True)
            sub.attributes("-topmost", True)
            sub.configure(bg="#1e1e1e")
            self._sub_popup = sub

            def _on_sub_click(e):
                if self._closed:
                    return
                if not self._is_mouse_inside():
                    self._close_all()

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
                    width=self.DEF_W,
                    cursor="hand2",
                )
                lbl.pack(fill="x", padx=0, pady=1, ipady=5)

                def on_click(event, _did=did, _dname=dname, _eid=eid):
                    elem_name = self._tree[_eid]["name"]
                    self._closed = True
                    self._unbind()
                    self._master.after(0, lambda: self._on_select(elem_name, _dname, _did))
                    try:
                        sub.destroy()
                    except Exception:
                        pass
                    try:
                        popup.destroy()
                    except Exception:
                        pass

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
            self._bind_recursive(sub, "<ButtonPress>", _on_sub_click)

        _active_lbl = [None]

        for eid, edata in items:
            ename = edata["name"]
            short = ename if len(ename) <= 30 else ename[:29] + "…"

            def make_row(parent, _eid=eid, _short=short):
                lbl = tk.Label(
                    parent,
                    text=f" {_short} ▶",
                    bg="#252525",
                    fg="#d0d0d0",
                    font=("Segoe UI", self.FONT_SZ),
                    anchor="w",
                    cursor="hand2",
                )
                lbl.pack(fill="x", padx=0, pady=0, ipady=5)

                def on_enter(e, w=lbl):
                    if _active_lbl[0] and _active_lbl[0] is not w:
                        _active_lbl[0].configure(bg="#252525", fg="#d0d0d0")
                    _active_lbl[0] = w
                    w.configure(bg="#2b579a", fg="white")
                    show_defects(_eid, w)

                lbl.bind("<Enter>", on_enter)
                return lbl

            sl.add_row(make_row)

        popup_h = sl.compute_height()
        sl.pack(fill="both", expand=True)

        popup.update_idletasks()
        popup.geometry(f"{self.ELEM_W}x{popup_h}+{bx}+{by}")

        popup.after(100, self._on_show)
        popup.after(200, self._poll_focus)
