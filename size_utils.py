"""
size_utils.py

Спільні функції для аналізу розміру файлів і папок.
Використовується в disk_analyzer.py та folder_analyzer.py.
"""

import os


# ============================================================
# ПАПКИ, ЯКІ ЗАВЖДИ ПРОПУСКАЄМО
# ============================================================

SKIP_DIRS = {
    "$Recycle.Bin",
    "System Volume Information",
}


# ============================================================
# КОНВЕРТАЦІЯ
# ============================================================

def bytes_to_gb(size: int) -> float:
    return size / (1024 ** 3)


# ============================================================
# РОЗМІР ПАПКИ (РЕКУРСИВНО)
# ============================================================

def get_size(path) -> int:
    """
    Рекурсивно рахує розмір файлу або папки в байтах.
    Пропускає системні папки без доступу.
    """

    total = 0

    try:

        for root, dirs, files in os.walk(path, topdown=True):

            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS
            ]

            for file in files:

                try:

                    file_path = os.path.join(root, file)

                    total += os.path.getsize(file_path)

                except (PermissionError, FileNotFoundError, OSError):
                    continue

    except (PermissionError, FileNotFoundError, OSError):
        pass

    return total