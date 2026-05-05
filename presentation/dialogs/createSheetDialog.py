import datetime
import tkinter as tk
import tkinter.messagebox as msg
import customtkinter as ctk

from shared.utils.dateUtils import parse_date_input, fmt_date
from shared.widgets.datePicker import InlineDatePicker
from shared import popupManager

class ScrollableDropdown:
    """
    Кастомный выпадающий список с прокруткой колёсиком мыши.
    Закрывается при клике вне списка, Esc и Alt+Tab.
    Без системного скроллбара — свои стрелки вверх/вниз.
    """

    MAX_VISIBLE = 12
    ROW_HEIGHT = 24
    ARROW_H = 18
    ARROW_BG = "#1a2840"
    ARROW_FG = "#6a9fd8"

    def __init__(self, parent, values, variable, width=300, placeholder="Выберите…", on_select=None):
        self._parent = parent
        self._values = list(values)
        self._var = variable
        self._width = width
        self._placeholder = placeholder
        self._on_select = on_select
        self._popup = None
        self._lb = None
        self._arrow_top = None
        self._arrow_bot = None
        self._root = None
        self._closed = True
        self._key_id = None
        self._focusout_id = None
        self._unmap_id = None
        self._click_outside_id = None

        self.widget = ctk.CTkButton(
            parent,
            textvariable=variable,
            width=width,
            height=32,
            fg_color="gray25",
            hover_color="gray30",
            text_color=("gray10", "gray90"),
            anchor="w",
            command=self._toggle,
        )
        if not variable.get():
            variable.set(placeholder)
        variable.trace_add("write", self._on_var_change)

    def set_values(self, values):
        self._values = list(values)
        self._var.set(self._placeholder)
        if self._popup:
            self._close()

    def get(self):
        v = self._var.get()
        return None if v == self._placeholder else v

    def _on_var_change(self, *_):
        v = self._var.get()
        color = "gray55" if v == self._placeholder else ("gray10", "gray90")
        self.widget.configure(text_color=color)

    def _toggle(self):
        if self._popup and self._popup.winfo_exists():
            self._close()
        else:
            self._open()

    def _open(self):
        if not self._values:
            return

        self.widget.update_idletasks()
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        actual_width = self.widget.winfo_width()

        visible = min(len(self._values), self.MAX_VISIBLE)
        need_scroll = len(self._values) > visible
        arrows_h = (2 * self.ARROW_H) if need_scroll else 0
        lb_h = visible * self.ROW_HEIGHT + 4
        total_h = lb_h + arrows_h

        popup = tk.Toplevel(self._parent)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.geometry(f"{actual_width}x{total_h}+{x}+{y}")
        popup.configure(bg=self.ARROW_BG)
        self._popup = popup
        self._closed = False
        popupManager.register(self)

        # --- Верхняя стрелка ---
        self._arrow_top = tk.Frame(popup, bg=self.ARROW_BG, height=self.ARROW_H)
        self._arrow_top.pack_propagate(False)
        tk.Label(self._arrow_top, text="▲", bg=self.ARROW_BG, fg=self.ARROW_FG, font=("Segoe UI", 8)).pack(expand=True)

        # --- Listbox (без скроллбара) ---
        lb = tk.Listbox(
            popup,
            bg="#2b2b2b",
            fg="#e0e0e0",
            selectbackground="#2b579a",
            selectforeground="white",
            activestyle="none",
            font=("Segoe UI", 13),
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        lb.pack(fill="both", expand=True)
        self._lb = lb

        # --- Нижняя стрелка ---
        self._arrow_bot = tk.Frame(popup, bg=self.ARROW_BG, height=self.ARROW_H)
        self._arrow_bot.pack_propagate(False)
        tk.Label(self._arrow_bot, text="▼", bg=self.ARROW_BG, fg=self.ARROW_FG, font=("Segoe UI", 8)).pack(expand=True)

        if need_scroll:
            self._arrow_top.pack(side="top", fill="x", before=lb)
            self._arrow_bot.pack(side="bottom", fill="x")
            self._arrow_top.bind("<Button-1>", lambda e: self._scroll(-1))
            self._arrow_bot.bind("<Button-1>", lambda e: self._scroll(1))
            for w in self._arrow_top.winfo_children():
                w.bind("<Button-1>", lambda e: self._scroll(-1))
            for w in self._arrow_bot.winfo_children():
                w.bind("<Button-1>", lambda e: self._scroll(1))

        for item in self._values:
            lb.insert("end", f"  {item}")

        current = self._var.get()
        if current != self._placeholder and current in self._values:
            idx = self._values.index(current)
            lb.selection_set(idx)
            lb.see(idx)

        def on_wheel(event):
            lb.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self._update_arrows()

        lb.bind("<MouseWheel>", on_wheel)
        popup.bind("<MouseWheel>", on_wheel)

        def select(event=None):
            sel = lb.curselection()
            if sel:
                value = self._values[sel[0]]
                self._var.set(value)
                self._close()
                if self._on_select:
                    self._on_select(value)

        lb.bind("<ButtonRelease-1>", select)
        lb.bind("<Return>", select)

        self._update_arrows()
        self._root = self._parent.winfo_toplevel()
        self._key_id = self._root.bind("<KeyPress>", self._on_key, add="+")
        self._focusout_id = self._root.bind("<FocusOut>", self._on_focusout, add="+")
        self._unmap_id = self._root.bind("<Unmap>", self._on_unmap, add="+")
        self._click_outside_id = self._root.bind("<Button-1>", self._on_click_outside, add="+")
        popup.after(200, self._poll_focus)

        popup.focus_set()

    def _scroll(self, direction):
        if self._lb:
            self._lb.yview_scroll(direction, "units")
            self._update_arrows()

    def _update_arrows(self):
        if not self._lb or not self._popup:
            return
        if not (self._arrow_top and self._arrow_bot):
            return
        try:
            top, bot = self._lb.yview()
            if top <= 0.001:
                self._arrow_top.configure(bg="#111a2a")
                for w in self._arrow_top.winfo_children():
                    w.configure(bg="#111a2a", fg="#3a5a78")
            else:
                self._arrow_top.configure(bg=self.ARROW_BG)
                for w in self._arrow_top.winfo_children():
                    w.configure(bg=self.ARROW_BG, fg=self.ARROW_FG)

            if bot >= 0.999:
                self._arrow_bot.configure(bg="#111a2a")
                for w in self._arrow_bot.winfo_children():
                    w.configure(bg="#111a2a", fg="#3a5a78")
            else:
                self._arrow_bot.configure(bg=self.ARROW_BG)
                for w in self._arrow_bot.winfo_children():
                    w.configure(bg=self.ARROW_BG, fg=self.ARROW_FG)
        except Exception:
            pass

    def _on_key(self, e):
        if e.keysym == "Escape":
            self._close()

    def _on_focusout(self, e):
        if self._closed:
            return

        if self._popup:
            self._popup.after(150, self._check_focus_lost)

    def _on_unmap(self, e):
        if self._closed:
            return
        if e.widget == self._root:
            self._close()

    def _on_click_outside(self, e):
        """Закрывает попап при клике вне его области."""
        if self._closed or not self._popup:
            return
        try:
            px = self._popup.winfo_rootx()
            py = self._popup.winfo_rooty()
            pw = self._popup.winfo_width()
            ph = self._popup.winfo_height()
            # Координаты клика в экранных координатах
            ex = e.widget.winfo_rootx() + e.x
            ey = e.widget.winfo_rooty() + e.y
            # Также проверяем, не кликнули ли по самой кнопке виджета
            bx = self.widget.winfo_rootx()
            by = self.widget.winfo_rooty()
            bw = self.widget.winfo_width()
            bh = self.widget.winfo_height()
            in_popup = px <= ex <= px + pw and py <= ey <= py + ph
            in_button = bx <= ex <= bx + bw and by <= ey <= by + bh
            if not in_popup and not in_button:
                self._close()
        except Exception:
            self._close()

    def _check_focus_lost(self):
        if self._closed:
            return
        try:
            focused = self._root.focus_get()
            if focused is None:
                self._close()
                return
            focused_top = focused.winfo_toplevel()
            if focused_top != self._root and focused_top != self._popup:
                self._close()
        except Exception:
            self._close()

    def _is_mouse_inside(self):
        if not self._popup or not self._popup.winfo_exists():
            return False
        try:
            mx = self._root.winfo_pointerx()
            my = self._root.winfo_pointery()
            x = self._popup.winfo_rootx()
            y = self._popup.winfo_rooty()
            w = self._popup.winfo_width()
            h = self._popup.winfo_height()
            return x <= mx <= x + w and y <= my <= y + h
        except Exception:
            return False

    def _poll_focus(self):
        if self._closed or not self._popup:
            return
        try:
            focused = self._root.focus_get()
            if focused is None:
                self._close()
                return
            focused_top = focused.winfo_toplevel()
            if focused_top != self._root and focused_top != self._popup:
                self._close()
                return
        except Exception:
            self._close()
            return
        try:
            self._popup.after(150, self._poll_focus)
        except Exception:
            pass

    def _close(self):
        if self._closed:
            return
        self._closed = True
        if self._root:
            for bid, event in [
                (self._key_id, "<KeyPress>"),
                (self._focusout_id, "<FocusOut>"),
                (self._unmap_id, "<Unmap>"),
                (self._click_outside_id, "<Button-1>"),
            ]:
                if bid:
                    try:
                        self._root.unbind(event, bid)
                    except Exception:
                        pass
        self._key_id = None
        self._focusout_id = None
        self._unmap_id = None
        self._click_outside_id = None
        popupManager.unregister(self)
        try:
            if self._popup:
                self._popup.destroy()
        except Exception:
            pass
        self._popup = None
        self._lb = None
        self._arrow_top = None
        self._arrow_bot = None

# ══════════════════════════════════════════════════════════════════════════════
#  CreateSheetDialog
# ══════════════════════════════════════════════════════════════════════════════

class CreateSheetDialog(ctk.CTkToplevel):
    """Модальный диалог создания нового листка осмотра."""

    def __init__(self, master, refs, on_created):
        super().__init__(master)
        self.title("Создать листок осмотра")
        self.geometry("620x450")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())

        self._refs = refs
        self._on_created = on_created
        self._build()

    def _build(self):
        refs = self._refs

        self._filial_var = ctk.StringVar()
        self._voltage_var = ctk.StringVar()
        self._line_var = ctk.StringVar()
        self._date_var = ctk.StringVar(value=datetime.date.today().strftime("%d.%m.%Y"))
        self._creator_var = ctk.StringVar()

        def labeled_row(label_text):
            f = ctk.CTkFrame(self, fg_color="transparent")
            f.pack(fill="x", padx=24, pady=6)
            ctk.CTkLabel(f, text=label_text, width=130, anchor="e").pack(side="left")
            inner = ctk.CTkFrame(f, fg_color="transparent")
            inner.pack(side="left", padx=8, fill="x", expand=True)
            return inner

        p = labeled_row("Филиал:")
        self._dd_filial = ScrollableDropdown(
            p,
            values=[f[1] for f in refs.filials],
            variable=self._filial_var,
            width=300,
            placeholder="Выберите филиал…",
            on_select=self._on_filial,
        )
        self._dd_filial.widget.pack(fill="x")

        p = labeled_row("Напряжение:")
        self._dd_voltage = ScrollableDropdown(
            p,
            values=[],
            variable=self._voltage_var,
            width=300,
            placeholder="Сначала выберите филиал…",
            on_select=self._on_voltage,
        )
        self._dd_voltage.widget.pack(fill="x")

        p = labeled_row("Линия:")
        self._dd_line = ScrollableDropdown(
            p,
            values=[],
            variable=self._line_var,
            width=300,
            placeholder="Сначала выберите напряжение…",
        )
        self._dd_line.widget.pack(fill="x")

        df = ctk.CTkFrame(self, fg_color="transparent")
        df.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(df, text="Дата осмотра:", width=130, anchor="e").pack(side="left")
        self._date_entry = ctk.CTkEntry(df, textvariable=self._date_var, width=120)
        self._date_entry.pack(side="left", padx=8)
        self._date_entry.bind("<Button-1>", self._pick_date)

        p = labeled_row("Создал ФИО:")
        ctk.CTkEntry(p, textvariable=self._creator_var, placeholder_text="Иванов И.И.", width=300).pack(fill="x")

        ctk.CTkButton(
            self,
            text="✅  Создать",
            command=self._confirm,
            fg_color="#2b579a",
            hover_color="#3a6abf",
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(pady=16)
        self.bind("<Return>", lambda e: self._confirm())

    def _pick_date(self, event=None):
        iso = parse_date_input(self._date_var.get())
        InlineDatePicker(
            master=self,
            anchor_widget=self._date_entry,
            date_var=self._date_var,
            initial_iso=iso,
        )

    def _on_filial(self, choice):
        refs = self._refs
        fid = next((f[0] for f in refs.filials if f[1] == choice), None)
        self._dd_voltage.set_values([v[1] for v in refs.voltages if v[2] == fid] if fid else [])
        self._dd_line.set_values([])

    def _on_voltage(self, choice):
        refs = self._refs
        filial = self._filial_var.get()
        fid = next((f[0] for f in refs.filials if f[1] == filial), None)
        vid = next((v[0] for v in refs.voltages if v[1] == choice and v[2] == fid), None) if fid else None
        self._dd_line.set_values([l[1] for l in refs.lines if l[2] == vid] if vid else [])

    def _confirm(self):
        refs = self._refs
        filial = self._dd_filial.get()
        voltage = self._dd_voltage.get()
        line = self._dd_line.get()
        creator = self._creator_var.get().strip()
        date_str = self._date_var.get().strip()

        if not all([filial, voltage, line, creator, date_str]):
            msg.showwarning("Ошибка", "Заполните все поля!")
            return

        iso_date = parse_date_input(date_str)
        if not iso_date:
            msg.showerror("Ошибка", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return

        fid = next(f[0] for f in refs.filials if f[1] == filial)
        vid = next(v[0] for v in refs.voltages if v[1] == voltage and v[2] == fid)
        lid = next(l[0] for l in refs.lines if l[1] == line)

        self.destroy()
        self._on_created(fid, vid, lid, iso_date, creator)
