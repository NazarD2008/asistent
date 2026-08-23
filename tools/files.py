"""
tools/files.py
Робота з файлами та папками.
Видалення йде через кошик (send2trash), а не os.remove() —
тобто навіть підтверджену дію можна відкотити вручну, і вимагає підтвердження.
"""

import os
from permissions import requires_confirmation

try:
    import send2trash  # pip install Send2Trash
except ImportError:
    send2trash = None


def open_path(path: str) -> str:
    """Відкрити файл або папку в провіднику / стандартній програмі."""
    if not os.path.exists(path):
        return f"Шлях не знайдено: {path}"
    os.startfile(path)
    return f"Відкрито: {path}"


def _delete_question(path: str) -> str:
    size = _human_size(path)
    return f"Видалити:\n  {path}\n  Розмір: {size}\nФайл буде переміщено у кошик, не видалено назавжди."


@requires_confirmation(description_fn=_delete_question)
def delete(path: str) -> str:
    """Видалити файл або папку (у кошик, з підтвердженням)."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if send2trash is None:
        raise RuntimeError("Встанови залежність: pip install Send2Trash")
    send2trash.send2trash(path)
    return f"Видалено (у кошику): {path}"


def _human_size(path: str) -> str:
    try:
        size = os.path.getsize(path) if os.path.isfile(path) else _dir_size(path)
    except OSError:
        return "невідомо"
    for unit in ["Б", "КБ", "МБ", "ГБ"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ТБ"


def _dir_size(path: str) -> int:
    total = 0
    for root, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(root, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return total
