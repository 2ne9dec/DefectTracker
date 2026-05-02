import datetime
import tkinter as tk
import tkinter.messagebox as msg
import customtkinter as ctk

from shared.utils.dateUtils import parse_date_input, fmt_date
from shared.widgets.datePicker import DatePickerDialog

class ScrollableDropdown:
    """
    Кастомный выпадающий список с прокруткой колёсиком мыши.
    Автоматически закрывается при клике вне списка или нажатии Esc.
    """

    MAX_VISIBLE = 12
    ROW_HEIGHT = 24

    def __init__(self, parent, values, variable, width=300, placeholder="Выберите…", on_select=None):
        self._parent = parent
        self._values = list(values)
        self._var = variable
        self._width = width
        self._placeholder = placeholder
        self._on_select = on_select
        self._popup = None
        self._click_handler_id = None

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
        height = visible * self.ROW_HEIGHT + 4

        popup = tk.Toplevel(self._parent)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.geometry(f"{actual_width}x{height}+{x}+{y}")
        popup.configure(bg="#2b2b2b")
        self._popup = popup

        frame = tk.Frame(popup, bg="#2b2b2b")
        frame.pack(fill="both", expand=True, padx=0, pady=0)

        sb = tk.Scrollbar(frame, orient="vertical", bg="#3a3a3a", troughcolor="#2b2b2b", activebackground="#555")
        sb.pack(side="right", fill="y")

        lb = tk.Listbox(
            frame,
            yscrollcommand=sb.set,
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
        lb.pack(side="left", fill="both", expand=True)
        sb.config(command=lb.yview)

        for item in self._values:
            lb.insert("end", f"  {item}")

        current = self._var.get()
        if current != self._placeholder and current in self._values:
            idx = self._values.index(current)
            lb.selection_set(idx)
            lb.see(idx)

        def on_wheel(event):
            lb.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_wheel_linux(event):
            lb.yview_scroll(-1 if event.num == 4 else 1, "units")

        lb.bind("<MouseWheel>", on_wheel)
        lb.bind("<Button-4>", on_wheel_linux)
        lb.bind("<Button-5>", on_wheel_linux)
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
        popup.bind("<Escape>", lambda e: self._close())

        # ✅ Глобальный обработчик кликов для закрытия при клике вне списка
        self._bind_click_outside(popup)

        popup.focus_set()

    def _bind_click_outside(self, popup):
        """
        Привязывает обработчик кликов по всему приложению.
        Закрывает popup, если клик был вне его и вне кнопки.
        """

        def on_click_outside(event):
            # Проверяем, является ли виджет, по которому кликнули,
            # частью popup или кнопки
            widget = event.widget
            is_popup_child = False

            # Проверяем, не является ли виджет частью popup
            try:
                while widget:
                    if widget == popup or widget == self.widget:
                        is_popup_child = True
                        break
                    widget = widget.master
            except Exception:
                pass

            # Если клик не по popup и не по кнопке — закрываем
            if not is_popup_child:
                self._close()

        # Привязываемся ко всем событиям мыши на верхнем уровне
        # Используем bind_all для перехвата кликов в любом месте приложения
        self._click_handler_id = popup.bind_all("<Button-1>", on_click_outside, add="+")

    def _close(self):
        if self._popup:
            # ✅ Отвязываем глобальный обработчик
            if self._click_handler_id:
                try:
                    self._popup.unbind_all("<Button-1>", self._click_handler_id)
                except Exception:
                    # Fallback для старых версий tkinter
                    try:
                        self._popup.unbind_all("<Button-1>")
                    except Exception:
                        pass
                self._click_handler_id = None

            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None

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
        ctk.CTkEntry(df, textvariable=self._date_var, width=120).pack(side="left", padx=8)
        ctk.CTkButton(df, text="📅", width=36, command=self._pick_date).pack(side="left")

        p = labeled_row("ФИО создателя:")
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

    def _pick_date(self):
        iso = parse_date_input(self._date_var.get())
        result = DatePickerDialog.ask(self, initial_date=iso, title="Дата осмотра")
        if result:
            self._date_var.set(fmt_date(result))

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
