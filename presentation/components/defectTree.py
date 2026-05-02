import tkinter as tk

class DefectTree:
    """
    Всплывающее окно-дерево для выбора дефекта.
    Два столбца: элементы (слева) → дефекты (справа, по наведению).
    """

    ELEM_W = 230
    DEF_W = 320
    ROW_H = 28
    MAX_VIS = 18

    SEV_BG = {"critical": "#5c1a1a", "medium": "#4d3000", "low": "#1a3d1a"}
    SEV_FG = {"critical": "#ff8080", "medium": "#ffb347", "low": "#80e080"}

    def __init__(self, master, anchor_widget, tree: dict, on_select):
        """
        Args:
            master:        Родительское окно.
            anchor_widget: Кнопка, под которой позиционируется попап.
            tree:          Результат ReferenceRepository.get_defect_tree().
            on_select:     Callable(elem_name, defect_name, defect_id).
        """
        self._tree = tree
        self._on_select = on_select
        self._show(master, anchor_widget)

    def _show(self, master, anchor_widget):
        anchor_widget.update_idletasks()
        bx = anchor_widget.winfo_rootx()
        by = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 4

        popup = tk.Toplevel(master)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg="#1e1e1e")

        left = tk.Frame(popup, bg="#252525", width=self.ELEM_W)
        left.pack(side="left", fill="y")
        right = tk.Frame(popup, bg="#1a1a1a", width=self.DEF_W)

        _sub_labels: list = []

        def show_defects(eid: int):
            nonlocal _sub_labels
            for w in _sub_labels:
                w.destroy()
            _sub_labels = []

            defects = self._tree[eid]["defects"]
            right.pack(side="left", fill="y")

            for did, dname, sev in defects:
                bg = self.SEV_BG.get(sev, "#2a2a2a")
                fg = self.SEV_FG.get(sev, "#cccccc")
                short = dname if len(dname) <= 38 else dname[:37] + "…"
                lbl = tk.Label(
                    right,
                    text=f"  {short}",
                    bg=bg,
                    fg=fg,
                    font=("Segoe UI", 10),
                    height=1,
                    anchor="w",
                    width=self.DEF_W // 7,
                    cursor="hand2",
                )
                lbl.pack(fill="x", padx=0, pady=0, ipady=4)

                def on_click(event, _did=did, _dname=dname, _eid=eid):
                    elem_name = self._tree[_eid]["name"]
                    popup.destroy()
                    self._on_select(elem_name, _dname, _did)

                def on_enter(e, w=lbl, b=bg):
                    w.configure(bg="#3a5a8a")

                def on_leave(e, w=lbl, b=bg):
                    w.configure(bg=b)

                lbl.bind("<Button-1>", on_click)
                lbl.bind("<Enter>", on_enter)
                lbl.bind("<Leave>", on_leave)
                _sub_labels.append(lbl)

            n_elem = len(self._tree)
            n_def = len(defects)
            popup_h = max(n_elem, n_def) * self.ROW_H + 8
            popup.geometry(f"{self.ELEM_W + self.DEF_W}x{popup_h}+{bx}+{by}")

        elem_h = min(len(self._tree), self.MAX_VIS) * self.ROW_H + 8
        popup.geometry(f"{self.ELEM_W}x{elem_h}+{bx}+{by}")

        for eid, edata in sorted(self._tree.items(), key=lambda x: x[1]["name"]):
            ename = edata["name"]
            short = ename if len(ename) <= 28 else ename[:27] + "…"
            lbl = tk.Label(
                left,
                text=f"  {short}  ▶",
                bg="#252525",
                fg="#d0d0d0",
                font=("Segoe UI", 10),
                anchor="w",
                height=1,
                cursor="hand2",
            )
            lbl.pack(fill="x", padx=0, pady=0, ipady=4)

            def on_enter(e, _eid=eid, w=lbl):
                w.configure(bg="#2b579a", fg="white")
                show_defects(_eid)

            def on_leave(e, w=lbl):
                w.configure(bg="#252525", fg="#d0d0d0")

            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)

        def on_focus_out(e):
            try:
                popup.destroy()
            except Exception:
                pass

        popup.bind("<FocusOut>", on_focus_out)
        popup.bind("<Escape>", lambda e: popup.destroy())
        popup.focus_set()
