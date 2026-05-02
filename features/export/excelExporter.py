import datetime
import os
import tkinter.messagebox as msg
import openpyxl

from features.export.sheetFormatter import SheetFormatter
from shared.utils.fileUtils import safe_filename

class ExcelExporter:
    """Экспортирует дефекты листка в файл .xlsx с двумя листами."""

    def __init__(self, filial: str, voltage: str, line: str):
        self.filial = filial
        self.voltage = voltage
        self.line = line
        self._formatter = SheetFormatter()

    def export(self, data: list[tuple]) -> None:
        """
        Принимает все записи дефектов (активные + устранённые) и сохраняет .xlsx.

        data — результат DefectRepository.fetch_all_for_export().
        """
        wb = openpyxl.Workbook()

        ws1 = wb.active
        ws1.title = "Активные дефекты"
        active_rows = [r for r in data if r[8] == "Активен"]
        self._formatter.fill_sheet(
            ws1,
            active_rows,
            f"Активные дефекты: {self.line}",
            self.filial,
            self.voltage,
            show_fix_cols=False,
        )

        ws2 = wb.create_sheet("Устранено")
        fixed_rows = [r for r in data if r[8] == "Устранено"]
        self._formatter.fill_sheet(
            ws2,
            fixed_rows,
            f"Устранённые дефекты: {self.line}",
            self.filial,
            self.voltage,
            show_fix_cols=True,
        )

        safe = safe_filename(self.line)
        filename = f"Листок_{safe}_{datetime.date.today():%Y-%m-%d}.xlsx"
        wb.save(filename)
        msg.showinfo("Экспорт", f"Файл сохранён:\n{os.path.abspath(filename)}")
