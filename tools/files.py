"""JARVIS file and folder tools."""

import os

from permissions import requires_confirmation

try:
    import send2trash
except ImportError:
    send2trash = None

SEARCH_SKIP_DIRS = {"AppData", ".git", "__pycache__", "node_modules", "venv"}
_last_file_matches = []


def _search_roots():
    home = os.path.expanduser("~")
    return [os.path.join(home, "Desktop"), os.path.join(home, "Documents"), os.path.join(home, "Downloads")]


def _find_file_paths(name: str, limit: int = 10):
    name = os.path.basename(str(name).strip().strip('"'))
    if not name:
        return []
    wanted = name.lower()
    matches, seen = [], set()
    for root in _search_roots():
        if not os.path.isdir(root):
            continue
        try:
            for current_root, dirs, filenames in os.walk(root):
                dirs[:] = [d for d in dirs if d not in SEARCH_SKIP_DIRS]
                for filename in filenames:
                    if filename.lower() != wanted:
                        continue
                    full = os.path.abspath(os.path.join(current_root, filename))
                    key = os.path.normcase(full)
                    if key in seen:
                        continue
                    seen.add(key)
                    matches.append(full)
                    if len(matches) >= limit:
                        return matches
        except (OSError, PermissionError):
            continue
    return matches


def open_path(path: str) -> str:
    path = os.path.abspath(os.path.expanduser(str(path).strip().strip('"')))
    if not os.path.exists(path):
        return f"Шлях не знайдено: {path}"
    os.startfile(path)
    return f"Відкрито: {path}"


def find_file(name: str) -> str:
    global _last_file_matches
    matches = _find_file_paths(name)
    _last_file_matches = matches
    clean_name = os.path.basename(str(name).strip().strip('"'))
    if not matches:
        return f"Файл не знайдено: {clean_name}"
    if len(matches) == 1:
        os.startfile(matches[0])
        _last_file_matches = []
        return f"Знайшов і відкрив: {matches[0]}"
    return "Знайшов файли:\n" + "\n".join(f"{i}. {path}" for i, path in enumerate(matches, 1))


def open_file(name: str) -> str:
    global _last_file_matches
    matches = _find_file_paths(name)
    _last_file_matches = matches
    clean_name = os.path.basename(str(name).strip().strip('"'))
    if not matches:
        return f"Файл не знайдено: {clean_name}"
    if len(matches) > 1:
        return "Знайшов кілька файлів:\n" + "\n".join(f"{i}. {path}" for i, path in enumerate(matches, 1)) + "\nСкажи номер потрібного файлу."
    os.startfile(matches[0])
    _last_file_matches = []
    return f"Відкриваю файл: {matches[0]}"


def open_file_number(number) -> str:
    global _last_file_matches
    try:
        index = int(number)
    except (ValueError, TypeError):
        return "Не зрозумів номер файлу."
    if not _last_file_matches:
        return "Немає активного списку файлів."
    if index < 1 or index > len(_last_file_matches):
        return f"У списку немає файлу номер {index}."
    path = _last_file_matches[index - 1]
    os.startfile(path)
    _last_file_matches = []
    return f"Відкриваю файл: {path}"


def find_folder(name: str) -> str:
    name = str(name).strip().strip('"')
    if not name:
        return "Не вказана назва папки."
    wanted = name.lower()
    home = os.path.expanduser("~")
    common = {
        "downloads": os.path.join(home, "Downloads"),
        "завантаження": os.path.join(home, "Downloads"),
        "desktop": os.path.join(home, "Desktop"),
        "робочий стіл": os.path.join(home, "Desktop"),
        "documents": os.path.join(home, "Documents"),
        "документи": os.path.join(home, "Documents"),
        "pictures": os.path.join(home, "Pictures"),
        "зображення": os.path.join(home, "Pictures"),
        "videos": os.path.join(home, "Videos"),
        "відео": os.path.join(home, "Videos"),
        "music": os.path.join(home, "Music"),
        "музика": os.path.join(home, "Music"),
    }
    direct = common.get(wanted)
    if direct and os.path.isdir(direct):
        os.startfile(direct)
        return f"Знайшов і відкрив папку: {direct}"

    matches, seen = [], set()
    for root in _search_roots():
        if not os.path.isdir(root):
            continue
        try:
            for current_root, dirs, _ in os.walk(root):
                dirs[:] = [d for d in dirs if d not in SEARCH_SKIP_DIRS]
                for dirname in dirs:
                    if dirname.lower() != wanted:
                        continue
                    full = os.path.abspath(os.path.join(current_root, dirname))
                    key = os.path.normcase(full)
                    if key in seen:
                        continue
                    seen.add(key)
                    matches.append(full)
                    if len(matches) >= 10:
                        break
                if len(matches) >= 10:
                    break
        except (OSError, PermissionError):
            continue
        if len(matches) >= 10:
            break
    if not matches:
        return f"Папку не знайдено: {name}"
    if len(matches) == 1:
        os.startfile(matches[0])
        return f"Знайшов і відкрив папку: {matches[0]}"
    return "Знайшов папки:\n" + "\n".join(f"{i}. {path}" for i, path in enumerate(matches, 1))


def _delete_question(path: str) -> str:
    return f"Видалити:\n  {path}\nРозмір: {_human_size(path)}\nФайл буде переміщено у кошик, не видалено назавжди."


@requires_confirmation(description_fn=_delete_question)
def delete(path: str) -> str:
    path = os.path.abspath(os.path.expanduser(str(path).strip().strip('"')))
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if send2trash is None:
        raise RuntimeError("Встанови залежність: pip install Send2Trash")
    send2trash.send2trash(path)
    return f"Видалено (у кошику): {path}"


def delete_file(name: str) -> str:
    matches = _find_file_paths(name)
    clean_name = os.path.basename(str(name).strip().strip('"'))
    if not matches:
        return f"Файл не знайдено: {clean_name}"
    if len(matches) > 1:
        return "Знайшов кілька файлів:\n" + "\n".join(f"{i}. {path}" for i, path in enumerate(matches, 1)) + "\nСкажи номер потрібного файлу, щоб видалити його."
    return delete(matches[0])


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
        for filename in filenames:
            fp = os.path.join(root, filename)
            try:
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
            except OSError:
                continue
    return total
