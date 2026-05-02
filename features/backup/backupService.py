"""
Резервное копирование и восстановление базы данных.

В оригинальном app1.py этот функционал упоминался в шапке комментария,
но сам код не был представлен. Добавьте реализацию сюда.
"""

import shutil
import datetime
import os
import tkinter.messagebox as msg

from app.config import DB_PATH
from app.logger import get_logger

logger = get_logger(__name__)

class BackupService:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def create_backup(self, backup_dir: str = ".") -> str | None:
        """Создаёт резервную копию БД. Возвращает путь к файлу или None при ошибке."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(backup_dir, f"defects_backup_{timestamp}.db")
            shutil.copy2(self.db_path, dest)
            logger.info(f"Backup created: {dest}")
            msg.showinfo("Резервная копия", f"Сохранено:\n{os.path.abspath(dest)}")
            return dest
        except Exception as e:
            logger.error(f"Backup error: {e}")
            msg.showerror("Ошибка", str(e))
            return None

    def restore_backup(self, backup_path: str) -> bool:
        """Восстанавливает БД из резервной копии. Возвращает True при успехе."""
        try:
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Restored from: {backup_path}")
            msg.showinfo(
                "Восстановление", "База данных восстановлена.\nПерезапустите приложение."
            )
            return True
        except Exception as e:
            logger.error(f"Restore error: {e}")
            msg.showerror("Ошибка", str(e))
            return False
