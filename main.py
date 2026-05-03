import sqlite3
import tkinter.messagebox as msg
import customtkinter as ctk

from app.config import DB_PATH
from app.database import ensure_db
from app.logger import get_logger

from features.inspectionSheet.service import InspectionSheetService
from features.defect.service import DefectService
from features.references.referenceService import ReferenceService
from features.export.excelExporter import ExcelExporter
from features.backup.backupService import BackupService

from presentation.mixins import AppMixins
from presentation.screens.startScreen import StartScreen
from presentation.screens.sheetScreen import SheetScreen
from presentation.dialogs.createSheetDialog import CreateSheetDialog

logger = get_logger(__name__)

class DefectApp(ctk.CTk, AppMixins):
    """
    Корневое окно приложения.
    Отвечает только за навигацию между экранами и инициализацию сервисов.
    Логика вынесена в features/, отображение — в presentation/.
    """

    def __init__(self):
        super().__init__()
        self.title("Дефекты ЛЭП")
        self.geometry("1280x760")
        self.after(0, self._maximize)

        # Проверка БД
        if not ensure_db(DB_PATH):
            self.destroy()
            return

        # Подключение к БД
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()

        # Сервисы
        self._ref_service = ReferenceService(self.cursor)
        self._ref_service.load()
        self._sheet_service = InspectionSheetService(self.conn, self.cursor)
        self._defect_service = DefectService(self.conn, self.cursor)
        self._backup_service = BackupService(DB_PATH)

        # Контекст текущего открытого листка
        self.current_sheet_id: int | None = None
        self.current_filial: str = ""
        self.current_voltage: str = ""
        self.current_line: str = ""
        self.current_pole_count: int = 0

        self._build_header()
        self._header_bar.pack_forget()  # скрыт на главном экране
        self._show_start()

    # ─────────────────────── HEADER ─────────────────────────────────────────

    def _build_header(self):
        self._header_bar = ctk.CTkFrame(self, fg_color="#1a3a6b", corner_radius=0)
        self._header_bar.pack(fill="x")
        inner = ctk.CTkFrame(self._header_bar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=8)

        self._back_btn = ctk.CTkButton(
            inner,
            text="← Назад",
            width=90,
            height=32,
            fg_color="#2b579a",
            hover_color="#3a6abf",
            command=self._show_start,
        )

    # ─────────────────────── НАВИГАЦИЯ ──────────────────────────────────────

    def _show_start(self):
        """Переключиться на главный экран (список листков)."""
        self._clear_content()
        self._back_btn.pack_forget()
        self._header_bar.pack_forget()
        self.current_sheet_id = None

        sheets = self._sheet_service.get_all()
        StartScreen(
            parent=self._content,
            sheets=sheets,
            on_create=self._open_create_dialog,
            on_open=self._open_sheet,
            on_delete=self._delete_sheet,
            on_backup=self._backup_service.create_backup,
        )

    def _open_sheet(self, sheet_id: int):
        """Переключиться на экран листка осмотра."""
        ctx = self._sheet_service.get_context(sheet_id)
        if not ctx:
            msg.showerror("Ошибка", "Листок не найден.")
            return

        filial, voltage, line, line_id, pole_count = ctx
        self.current_sheet_id = sheet_id
        self.current_filial = filial
        self.current_voltage = voltage
        self.current_line = line
        self.current_pole_count = pole_count or 0

        self._clear_content()

        SheetScreen(
            parent=self._content,
            sheet_id=sheet_id,
            filial=filial,
            voltage=voltage,
            line=line,
            pole_count=self.current_pole_count,
            defect_service=self._defect_service,
            ref_service=self._ref_service,
            on_export=self._export_current_sheet,
            on_back=self._show_start,
        )

    # ─────────────────────── ЛИСТКИ ─────────────────────────────────────────

    def _open_create_dialog(self):
        CreateSheetDialog(
            master=self,
            refs=self._ref_service,
            on_created=self._on_sheet_created,
        )

    def _on_sheet_created(
        self,
        filial_id: int,
        voltage_id: int,
        line_id: int,
        created_date: str,
        created_by: str,
    ):
        new_id = self._sheet_service.create(filial_id, voltage_id, line_id, created_date, created_by)
        self._open_sheet(new_id)

    def _delete_sheet(self, sheet_id: int):
        if msg.askyesno("Подтверждение", "Удалить листок осмотра и все его дефекты?"):
            self._sheet_service.delete(sheet_id)
            self._show_start()

    # ─────────────────────── ЭКСПОРТ ────────────────────────────────────────

    def _export_current_sheet(self):
        if not self.current_sheet_id:
            return
        data = self._defect_service.fetch_all_for_export(self.current_sheet_id)
        exporter = ExcelExporter(
            filial=self.current_filial,
            voltage=self.current_voltage,
            line=self.current_line,
        )
        exporter.export(data)

    # ─────────────────────── ВСПОМОГАТЕЛЬНОЕ ─────────────────────────────────

    def _clear_content(self):
        """Удаляет текущий контент-фрейм и создаёт новый."""
        if hasattr(self, "_content"):
            self._content.destroy()
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True)

    def on_close(self):
        try:
            self.conn.close()
        except Exception:
            pass
        self.destroy()

def main():
    app = DefectApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

if __name__ == "__main__":
    main()
