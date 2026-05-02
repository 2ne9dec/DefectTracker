import os
import sys
import re

def get_db_path() -> str:
    """
    Определяет путь к файлу базы данных defects.db.

    - В режиме .exe (PyInstaller): рядом с исполняемым файлом.
    - В режиме .py-скрипта: в текущей рабочей директории.
    """
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "defects.db")
    return "defects.db"


def safe_filename(name: str, max_len: int = 25) -> str:
    """Очищает строку для использования в имени файла."""
    return re.sub(r"[^\w\-\.]", "_", name)[:max_len]
