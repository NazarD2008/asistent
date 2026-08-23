"""
tools/files.py
Робота з файлами та папками.
"""

import os
from permissions import requires_confirmation

try:
    import send2trash
except ImportError:
    send2trash = None


def open_path(path: str) -> str:
    """Відкрити файл або папку в провіднику / стандартній програмі."""
    if not os.path.exists(path):
        return f"Шлях не знайдено: {path}"
    os.startfile(path)
    return f"Відкрито: {path}"


def find_file(name: str) -> str:
    """Знайти файл локально, без Google/GPT."""
    name = os.path.basename(str(name).strip().strip('"'))
    if not name:
        return "Не вказана назва файлу."

    home = os.path.expanduser("~")
    roots = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Downloads"),
        home,
    ]
    roots = list(dict.fromkeys(r for r in roots if os.path.isdir(r)))

    skip_dirs = {"AppData", ".git", "__pycache__", "node_modules", "venv"}
    wanted = name.lower()
    matches = []

    for root in roots:
        try:
            for current_root, dirs, filenames in os.walk(root):
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                for filename in filenames:
                    if filename.lower() == wanted:
                        matches.append(os.path.join(current_root, filename))
                        if len(matches) >= 5:
                            break
                if len(matches) >= 5:
                    break
        except (OSError, PermissionError):
            continue
        if len(matches) >= 5:
            break

    if not matches:
        return f"Файл не знайдено: {name}"

    if len(matches) == 1:
        os.startfile(matches[0])
        return f"Знайшов і відкрив: {matches[0]}"

    return "Знайшов файли:\n" + "\n".join(
        f"{i}. {path}" for i, path in enumerate(matches, 1)
    )


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
