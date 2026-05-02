import sqlite3
import tkinter.messagebox as msg

from features.references.repository import ReferenceRepository
from app.logger import get_logger

logger = get_logger(__name__)

class ReferenceService:
    """
    Кэширует справочные данные в памяти.
    Вызывать load() при старте и после изменений справочников.
    """

    def __init__(self, cursor: sqlite3.Cursor):
        self._repo = ReferenceRepository(cursor)
        self.filials: list[tuple] = []
        self.voltages: list[tuple] = []
        self.lines: list[tuple] = []
        self.elements: list[tuple] = []

    def load(self) -> None:
        """Загружает все справочники из БД в память."""
        try:
            self.filials = self._repo.get_filials()
            self.voltages = self._repo.get_voltages()
            self.lines = self._repo.get_lines()
            self.elements = self._repo.get_elements()
        except sqlite3.Error as e:
            logger.error(f"ReferenceService.load error: {e}")
            msg.showerror("Ошибка", str(e))

    def get_defect_tree(self) -> dict:
        return self._repo.get_defect_tree()
