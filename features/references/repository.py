import sqlite3

class ReferenceRepository:
    """Чтение справочных данных: Filial, Voltage, Line, Element."""

    def __init__(self, cursor: sqlite3.Cursor):
        self.cursor = cursor

    def get_filials(self) -> list[tuple]:
        """Возвращает список (id, name) всех филиалов."""
        self.cursor.execute("SELECT id, name FROM Filial ORDER BY name")
        return self.cursor.fetchall()

    def get_voltages(self) -> list[tuple]:
        """Возвращает список (id, name, filial_id) напряжений, отсортированных по кВ."""
        self.cursor.execute("""
            SELECT id, name, filial_id FROM Voltage ORDER BY
            CASE WHEN name LIKE '%35%' THEN 1 WHEN name LIKE '%110%' THEN 2
                WHEN name LIKE '%220%' THEN 3 WHEN name LIKE '%330%' THEN 4
                WHEN name LIKE '%750%' THEN 5 ELSE 6 END
        """)
        return self.cursor.fetchall()

    def get_lines(self) -> list[tuple]:
        """Возвращает список (id, name, voltage_id, pole_count) линий."""
        self.cursor.execute(
            "SELECT id, name, voltage_id, pole_count FROM Line ORDER BY name"
        )
        return self.cursor.fetchall()

    def get_elements(self) -> list[tuple]:
        """Возвращает список (id, name) элементов ЛЭП."""
        self.cursor.execute("SELECT id, name FROM Element ORDER BY name")
        return self.cursor.fetchall()

    def get_defect_tree(self) -> dict:
        """
        Возвращает дерево: elem_id → {name, defects: [(did, dname, severity)]}.
        Используется в DefectTree для выбора дефекта.
        """
        self.cursor.execute("""
            SELECT e.id, e.name, d.id, d.name, d.severity
            FROM Element e
            JOIN DefectType d ON d.element_id = e.id
            ORDER BY e.name, d.name
        """)
        rows = self.cursor.fetchall()
        tree: dict = {}
        for eid, ename, did, dname, sev in rows:
            if eid not in tree:
                tree[eid] = {"name": ename, "defects": []}
            tree[eid]["defects"].append((did, dname, sev))
        return tree
