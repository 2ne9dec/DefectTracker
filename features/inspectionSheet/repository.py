import sqlite3

class InspectionSheetRepository:

    def __init__(self, cursor: sqlite3.Cursor):
        self.cursor = cursor

    def get_all(self) -> list[tuple]:
        """
        Возвращает все листки осмотра с количеством активных и устранённых дефектов.
        Кортеж: (id, filial_name, voltage_name, line_name, created_date, created_by,
                status, active_count, fixed_count)
        """
        self.cursor.execute("""
            SELECT s.id, f.name, v.name, l.name, s.created_date, s.created_by, s.status,
                  (SELECT COUNT(*) FROM DefectRecord WHERE sheet_id=s.id AND is_fixed=0),
                  (SELECT COUNT(*) FROM DefectRecord WHERE sheet_id=s.id AND is_fixed=1)
            FROM InspectionSheet s
            JOIN Filial f ON s.filial_id=f.id
            JOIN Voltage v ON s.voltage_id=v.id
            JOIN Line l ON s.line_id=l.id
            ORDER BY s.created_date DESC
        """)
        return self.cursor.fetchall()

    def get_by_id(self, sheet_id: int) -> tuple | None:
        """
        Возвращает контекст листка: (filial_name, voltage_name, line_name, line_id, pole_count).
        """
        self.cursor.execute(
            "SELECT f.name, v.name, l.name, l.id, l.pole_count "
            "FROM InspectionSheet s "
            "JOIN Filial f ON s.filial_id=f.id "
            "JOIN Voltage v ON s.voltage_id=v.id "
            "JOIN Line l ON s.line_id=l.id WHERE s.id=?",
            (sheet_id,),
        )
        return self.cursor.fetchone()

    def create(
        self,
        filial_id: int,
        voltage_id: int,
        line_id: int,
        created_date: str,
        created_by: str,
    ) -> int:
        """Создаёт новый листок, возвращает его ID."""
        self.cursor.execute(
            "INSERT INTO InspectionSheet (filial_id,voltage_id,line_id,created_date,created_by,status)"
            " VALUES (?,?,?,?,?,'active')",
            (filial_id, voltage_id, line_id, created_date, created_by),
        )
        return self.cursor.lastrowid

    def delete(self, sheet_id: int) -> None:
        """Удаляет листок и все связанные дефекты."""
        self.cursor.execute("DELETE FROM DefectRecord WHERE sheet_id=?", (sheet_id,))
        self.cursor.execute("DELETE FROM InspectionSheet WHERE id=?", (sheet_id,))
