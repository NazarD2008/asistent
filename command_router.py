import re

from tools import apps


def normalize(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower().strip()
    text = text.replace("ё", "е").replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", text)


OPEN_WORDS = (
    "відкрий", "відкрити", "відкрив", "відкрой", "відкрйи", "відкри",
    "открой", "отрой", "запусти", "запустити", "включи", "включити",
    "увімкни", "увімкнути",
)

CLOSE_WORDS = (
    "закрий", "закрити", "закрой", "закрыть", "закрйи", "вимкни", "вимкнути",
)

SITES = {
    "ютуб мюзік": "https://music.youtube.com",
    "youtube music": "https://music.youtube.com",
    "ютуб": "https://www.youtube.com",
    "ютюб": "https://www.youtube.com",
    "youtube": "https://www.youtube.com",
    "гугл": "https://www.google.com",
    "google": "https://www.google.com",
    "тікток": "https://www.tiktok.com",
    "тик ток": "https://www.tiktok.com",
    "tiktok": "https://www.tiktok.com",
}


def _starts_with(command: str, words) -> bool:
    return any(command == word or command.startswith(word + " ") for word in words)


def _is_compound(command: str) -> bool:
    markers = (
        ",", " потім ", " і ", " та напиши ", " і напиши ", " напиши ", " введи ",
        " натисни ", " нажми ", " клікни ", " кликни ", " двічі ",
    )
    return any(marker in command for marker in markers)


def _find_app(command: str):
    aliases = sorted(apps.APP_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
    for phrase, app_name in aliases:
        if phrase in command:
            return app_name
    return None


def _route_app(command: str):
    if _is_compound(command):
        return None
    app_name = _find_app(command)
    if not app_name:
        return None
    if _starts_with(command, CLOSE_WORDS):
        return {"action": "close_app", "target": app_name}
    if _starts_with(command, OPEN_WORDS):
        return {"action": "open_app", "target": app_name}
    return None


def _route_site(command: str):
    if not _starts_with(command, OPEN_WORDS) or _is_compound(command):
        return None
    for name, url in sorted(SITES.items(), key=lambda item: len(item[0]), reverse=True):
        if name in command:
            return {"action": "open_url", "target": url}
    return None


def _route_browser(command: str):
    """Route browser-only commands before desktop UI and generic web search."""
    if _is_compound(command):
        return None
    youtube_markers = ("на ютубі", "на ютуб", "в ютубі", "в youtube", "на youtube", "ютуб відео", "youtube відео")
    search_prefixes = ("знайди ", "знайти ", "пошукай ", "пошук ", "відшукай ")
    if any(marker in command for marker in youtube_markers):
        for prefix in search_prefixes:
            if command.startswith(prefix):
                query = command[len(prefix):].strip()
                for marker in youtube_markers:
                    query = query.replace(marker, "").strip()
                if query:
                    return {"action": "browser_search", "target": f"youtube|{query}"}
    if command.startswith("відкрий сторінку "):
        target = command[len("відкрий сторінку "):].strip()
        if target:
            return {"action": "browser_open", "target": target}
    for prefix in ("натисни в браузері ", "натисни у браузері ", "нажми в браузері ", "нажми у браузері ", "клікни в браузері ", "клікни у браузері "):
        if command.startswith(prefix):
            target = command[len(prefix):].strip()
            if target:
                return {"action": "browser_click_text", "target": target}
    for prefix in ("введи в браузері ", "введи у браузері ", "напиши в браузері ", "напиши у браузері "):
        if command.startswith(prefix):
            target = command[len(prefix):].strip()
            if target:
                return {"action": "browser_type", "target": target}
    if command in ("що відкрито в браузері", "яка сторінка відкрито", "яка сторінка в браузері"):
        return {"action": "browser_current", "target": ""}
    return None


def _route_file(command: str):
    file_prefixes = (
        ("знайди файл ", "find_file"), ("знайти файл ", "find_file"),
        ("пошукай файл ", "find_file"), ("пошук файлу ", "find_file"),
        ("відкрий файл ", "open_file"), ("відкрити файл ", "open_file"),
        ("запусти файл ", "open_file"), ("видали файл ", "delete_file"),
        ("видалити файл ", "delete_file"), ("знищ файл ", "delete_file"),
    )
    for prefix, action in file_prefixes:
        if command.startswith(prefix):
            name = command[len(prefix):].strip()
            if name:
                return {"action": action, "target": name}
    for prefix in ("відкрий папку ", "відкрити папку ", "знайди папку ", "знайти папку "):
        if command.startswith(prefix):
            name = command[len(prefix):].strip()
            if name:
                return {"action": "find_folder", "target": name}
    return None


def _route_ui(command: str):
    if _is_compound(command):
        return None
    if any(phrase in command for phrase in ("покажи елементи інтерфейсу", "покажи елементи інтерфейса", "покажи ui", "проінспектуй вікно", "інспектуй вікно")):
        return {"action": "inspect_ui", "target": ""}
    for prefix in (
        "натисни кнопку ", "натисни на кнопку ", "натисни елемент ", "натисни на елемент ",
        "натисни на ", "нажми кнопку ", "нажми на кнопку ", "нажми елемент ", "нажми на елемент ",
        "нажми на ", "клікни кнопку ", "клікни елемент ", "клікни на ", "кликни кнопку ", "кликни елемент ", "кликни на ",
    ):
        if command.startswith(prefix):
            name = command[len(prefix):].strip()
            if name:
                return {"action": "ui_click", "target": name}
    if command in ("яке активне вікно", "що за вікно зараз активне"):
        return {"action": "foreground_window", "target": ""}
    return None


def _route_volume(command: str):
    if _is_compound(command):
        return None
    match = re.search(r"(?:звук|гучність|громкость)\s*(?:на|до)?\s*(\d{1,3})", command)
    if match:
        return {"action": "set_volume", "target": str(max(0, min(100, int(match.group(1)))))}
    if any(p in command for p in ("зроби голосніше", "зроби гучніше", "збільш звук", "додай гучності", "прибавь звук", "голосніше", "гучніше")):
        return {"action": "volume_up", "target": ""}
    if any(p in command for p in ("зроби тихіше", "зменш звук", "зменш гучність", "прибери гучність", "убавь звук", "тихіше")):
        return {"action": "volume_down", "target": ""}
    if any(p in command for p in ("вимкни звук", "выключи звук", "заглуши звук", "приглуши звук", "mute")):
        return {"action": "mute", "target": ""}
    if any(p in command for p in ("увімкни звук", "включи звук", "поверни звук", "unmute")):
        return {"action": "unmute", "target": ""}
    return None


def _number_from_word(word: str):
    return {"сто": 100, "стo": 100, "двісті": 200, "двісти": 200, "триста": 300, "чотириста": 400, "п'ятсот": 500, "пятсот": 500, "шістсот": 600, "шестсот": 600, "сімсот": 700, "семьсот": 700, "вісімсот": 800, "восемьсот": 800, "дев'ятсот": 900, "девятсот": 900}.get(word)


def _parse_xy(command: str):
    tokens = re.findall(r"\d{1,5}|[а-яіїєґ']+", command)
    values = []
    for token in tokens:
        value = int(token) if token.isdigit() else _number_from_word(token)
        if value is not None:
            values.append(value)
        if len(values) == 2:
            break
    return values if len(values) == 2 else None


def _route_computer(command: str):
    if _is_compound(command):
        return None
    if "скріншот" in command or "скриншот" in command:
        return {"action": "screenshot", "target": ""}
    if "координат" in command and "миш" in command:
        return {"action": "mouse_position", "target": ""}
    if any(word in command for word in ("перемісти миш", "перемісти курсор", "посунь миш", "посунь курсор")):
        xy = _parse_xy(command)
        if xy:
            return {"action": "mouse_move", "target": f"{xy[0]} {xy[1]}"}
    if any(word in command for word in ("двічі клікни", "двойной клик", "подвійний клік")):
        xy = _parse_xy(command)
        if xy:
            return {"action": "double_click", "target": f"{xy[0]} {xy[1]}"}
    if any(word in command for word in ("клікни", "кликни", "натисни мишкою", "натисни мишею")):
        xy = _parse_xy(command)
        if xy:
            return {"action": "click", "target": f"{xy[0]} {xy[1]}"}
    if any(word in command for word in ("напиши ", "введи ")):
        for prefix in ("напиши ", "введи "):
            if command.startswith(prefix):
                text = command[len(prefix):].strip()
                if text:
                    return {"action": "type_text", "target": text}
    if command.startswith("натисни ") and not command.startswith("натисни на "):
        key = command[len("натисни "):].strip()
        if key:
            return {"action": "press_key", "target": key}
    return None


def _route_music(command: str):
    if _is_compound(command):
        return None
    if not any(word in command for word in ("музику", "музика", "music")):
        return None
    if _starts_with(command, OPEN_WORDS):
        return {"action": "play_music", "target": ""}
    return None


def _route_search(command: str):
    if _is_compound(command):
        return None
    for prefix in ("знайди ", "знайти ", "пошукай ", "пошук "):
        if command.startswith(prefix):
            query = command[len(prefix):].strip()
            if query:
                return {"action": "web_search", "target": query}
    return None


def _route_system(command: str):
    if _is_compound(command):
        return None
    if command in ("вимкни комп", "вимкни комп'ютер", "вимкни пк", "выключи компьютер", "выключи пк", "вимкни машину"):
        return {"action": "shutdown", "target": ""}
    if command in ("перезавантаж комп", "перезавантаж комп'ютер", "перезавантаж пк", "перезапусти пк", "перезагрузи компьютер", "перезагрузи пк", "restart"):
        return {"action": "restart", "target": ""}
    return None


def route(command: str, context=None):
    if not command:
        return None
    normalized = normalize(command)
    if not normalized:
        return None
    for handler in (_route_app, _route_site, _route_browser, _route_file, _route_ui, _route_computer, _route_volume, _route_music, _route_search, _route_system):
        result = handler(normalized)
        if result is not None:
            print(f"[router] LOCAL: {result['action']} -> {result['target']}")
            return result
    print("[router] LOCAL: не визначено")
    return None
