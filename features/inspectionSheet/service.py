import sqlite3

from features.inspectionSheet.repository import InspectionSheetRepository
from app.logger import get_logger

logger = get_logger(__name__)

class InspectionSheetService:

    def __init__(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor):
        self.conn = conn
        self.cursor = cursor
        self._repo = InspectionSheetRepository(cursor)

    def get_all(self) -> list[tuple]:
        return self._repo.get_all()

    def get_context(self, sheet_id: int) -> tuple | None:
        """
        Возвращает контекст листка для заполнения current_* переменных приложения.
        (filial_name, voltage_name, line_name, line_id, pole_count)
        """
        return self._repo.get_by_id(sheet_id)

    def create(
        self,
        filial_id: int,
        voltage_id: int,
        line_id: int,
        created_date: str,
        created_by: str,
    ) -> int:
        new_id = self._repo.create(
            filial_id, voltage_id, line_id, created_date, created_by
        )
        self.conn.commit()
        logger.info(f"Created InspectionSheet id={new_id}")
        return new_id

    def delete(self, sheet_id: int) -> None:
        self._repo.delete(sheet_id)
        self.conn.commit()
        logger.info(f"Deleted InspectionSheet id={sheet_id}")
