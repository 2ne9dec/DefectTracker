import sqlite3

class DefectRepository:

    def __init__(self, cursor: sqlite3.Cursor):
        self.cursor = cursor

    def fetch_records(
        self,
        sheet_id: int,
        is_fixed: int,
        search: str = "",
    ) -> list[tuple]:
        """
        Возвращает дефекты листка с фильтрацией.
        Кортеж: (pole_number, element_name, defect_name, date_found, inspector_find,
                date_fixed, inspector_fix, is_fixed, severity, id)
        """
        q = """
            SELECT r.pole_number, e.name, d.name, r.date_found, r.inspector_find,
                  r.date_fixed, r.inspector_fix, r.is_fixed, d.severity, r.id
            FROM DefectRecord r
            JOIN DefectType d ON r.defect_id=d.id
            JOIN Element e ON d.element_id=e.id
            WHERE r.sheet_id=? AND r.is_fixed=?
        """
        params: list = [sheet_id, is_fixed]
        if search:
            q += " AND (LOWER(d.name) LIKE ? OR LOWER(e.name) LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY r.pole_number, e.name"
        self.cursor.execute(q, params)
        return self.cursor.fetchall()

    def fetch_all_for_export(self, sheet_id: int) -> list[tuple]:
        """
        Возвращает все дефекты листка (активные + устранённые) для экспорта в Excel.
        """
        self.cursor.execute(
            """
            SELECT r.pole_number, e.name, d.name, d.severity,
                  r.date_found, r.inspector_find,
                  r.date_fixed, r.inspector_fix,
                  CASE WHEN r.is_fixed=1 THEN 'Устранено' ELSE 'Активен' END
            FROM DefectRecord r
            JOIN DefectType d ON r.defect_id=d.id
            JOIN Element e ON d.element_id=e.id
            WHERE r.sheet_id=?
            ORDER BY r.is_fixed, r.pole_number
        """,
            (sheet_id,),
        )
        return self.cursor.fetchall()

    def get_defect_info(self, record_id: int) -> tuple | None:
        """Возвращает (element_name, defect_name, severity) для одной записи."""
        self.cursor.execute(
            "SELECT e.name, d.name, d.severity FROM DefectRecord r "
            "JOIN DefectType d ON r.defect_id=d.id "
            "JOIN Element e ON d.element_id=e.id WHERE r.id=?",
            (record_id,),
        )
        return self.cursor.fetchone()

    def get_active_by_pole(self, sheet_id: int, pole_number: int) -> list[tuple]:
        """Возвращает активные дефекты конкретной опоры: [(defect_id, inspector_find)]."""
        self.cursor.execute(
            "SELECT defect_id, inspector_find FROM DefectRecord "
            "WHERE sheet_id=? AND pole_number=? AND is_fixed=0",
            (sheet_id, pole_number),
        )
        return self.cursor.fetchall()

    def insert(
        self,
        sheet_id: int,
        pole_number: int,
        defect_id: int,
        date_found: str,
        inspector_find: str,
    ) -> None:
        self.cursor.execute(
            "INSERT INTO DefectRecord (sheet_id,pole_number,defect_id,date_found,inspector_find)"
            " VALUES (?,?,?,?,?)",
            (sheet_id, pole_number, defect_id, date_found, inspector_find),
        )

    def mark_fixed(self, record_id: int, date_fixed: str, inspector_fix: str) -> None:
        self.cursor.execute(
            "UPDATE DefectRecord SET is_fixed=1,date_fixed=?,inspector_fix=? WHERE id=?",
            (date_fixed, inspector_fix, record_id),
        )

    def delete_many(self, ids: list[int]) -> None:
        self.cursor.executemany(
            "DELETE FROM DefectRecord WHERE id=?", [(i,) for i in ids]
        )
