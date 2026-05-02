import sqlite3
import datetime

from features.defect.repository import DefectRepository
from app.logger import get_logger

logger = get_logger(__name__)

class DefectService:

    def __init__(self, conn: sqlite3.Connection, cursor: sqlite3.Cursor):
        self.conn = conn
        self.cursor = cursor
        self._repo = DefectRepository(cursor)

    def fetch_records(
        self, sheet_id: int, is_fixed: int, search: str = ""
    ) -> list[tuple]:
        return self._repo.fetch_records(sheet_id, is_fixed, search)

    def fetch_all_for_export(self, sheet_id: int) -> list[tuple]:
        return self._repo.fetch_all_for_export(sheet_id)

    def get_defects_info(self, record_ids: list[int]) -> list[dict]:
        """Загружает инфо о дефектах для отображения в диалоге устранения."""
        result = []
        for rid in record_ids:
            info = self._repo.get_defect_info(rid)
            if info:
                result.append(
                    {
                        "id": rid,
                        "element": info[0],
                        "defect": info[1],
                        "severity": info[2],
                    }
                )
        return result

    def add(
        self,
        sheet_id: int,
        pole_number: int,
        defect_id: int,
        date_found: str,
        inspector_find: str,
    ) -> None:
        self._repo.insert(sheet_id, pole_number, defect_id, date_found, inspector_find)
        self.conn.commit()
        logger.info(f"Added defect pole={pole_number} defect_id={defect_id}")

    def fix_many(
        self, record_ids: list[int], date_fixed: str, inspector_fix: str
    ) -> None:
        for rid in record_ids:
            self._repo.mark_fixed(rid, date_fixed, inspector_fix)
        self.conn.commit()
        logger.info(f"Fixed {len(record_ids)} defect(s)")

    def delete_many(self, ids: list[int]) -> None:
        self._repo.delete_many(ids)
        self.conn.commit()
        logger.info(f"Deleted defects: {ids}")

    def copy_pole(
        self,
        sheet_id: int,
        source_pole: int,
        target_poles: list[int],
        inspector: str,
        pole_count: int,
    ) -> int:
        """
        Копирует активные дефекты source_pole на target_poles.
        Возвращает количество созданных записей.
        Выбрасывает ValueError если опора вне диапазона.
        """
        src_defects = self._repo.get_active_by_pole(sheet_id, source_pole)
        if not src_defects:
            return 0

        today = datetime.date.today().isoformat()
        count = 0
        for target_pole in target_poles:
            if pole_count > 0 and not (1 <= target_pole <= pole_count):
                raise ValueError(f"Опора №{target_pole} вне диапазона 1–{pole_count}")
            for defect_id, _ in src_defects:
                self._repo.insert(sheet_id, target_pole, defect_id, today, inspector)
                count += 1

        self.conn.commit()
        logger.info(f"Copied {count} defect(s) from pole {source_pole} to {target_poles}")
        return count
