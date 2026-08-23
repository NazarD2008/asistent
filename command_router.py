import re

from tools import apps


def normalize(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower().strip()
    text = text.replace("ё", "е").replace("’", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text)
    return text


OPEN_WORDS = (
    "відкрий", "відкрити", "відкрив", "відкрой", "відкрйи", "відкри",
    "открой", "отрой", "запусти", "запустити", "включи",
    "включити", "увімкни", "увімкнути",
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


def _find_app(command: str):
    aliases = sorted(apps.APP_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
    for phrase, app_name in aliases:
        if phrase in command:
            return app_name
    return None


def _route_app(command: str):
    """Програми мають пріоритет над сайтами."""
    app_name = _find_app(command)
    if not app_name:
        return None

    if _starts_with(command, CLOSE_WORDS):
        return {"action": "close_app", "target": app_name}

    if _starts_with(command, OPEN_WORDS):
        return {"action": "open_app", "target": app_name}

    return None


def _route_site(command: str):
    if not _starts_with(command, OPEN_WORDS):
        return None

    for name, url in sorted(SITES.items(), key=lambda item: len(item[0]), reverse=True):
        if name in command:
            return {"action": "open_url", "target": url}
    return None


def _route_volume(command: str):
    match = re.search(r"(?:звук|гучність|громкость)\s*(?:на|до)?\s*(\d{1,3})", command)
    if match:
        return {"action": "set_volume", "target": str(max(0, min(100, int(match.group(1)))))}

    if any(p in command for p in (
        "зроби голосніше", "зроби гучніше", "збільш звук", "додай гучності",
        "прибавь звук", "голосніше", "гучніше"
    )):
        return {"action": "volume_up", "target": ""}

    if any(p in command for p in (
        "зроби тихіше", "зменш звук", "зменш гучність", "прибери гучність",
        "убавь звук", "тихіше"
    )):
        return {"action": "volume_down", "target": ""}

    if any(p in command for p in (
        "вимкни звук", "выключи звук", "заглуши звук", "приглуши звук", "mute"
    )):
        return {"action": "mute", "target": ""}

    if any(p in command for p in (
        "увімкни звук", "включи звук", "поверни звук", "unmute"
    )):
        return {"action": "unmute", "target": ""}

    return None


def _route_music(command: str):
    music_words = ("музику", "музика", "music")
    if not any(word in command for word in music_words):
        return None

    if _starts_with(command, OPEN_WORDS):
        return {"action": "play_music", "target": ""}
    return None


def _route_search(command: str):
    prefixes = ("знайди ", "знайти ", "пошукай ", "пошук ")
    for prefix in prefixes:
        if command.startswith(prefix):
            query = command[len(prefix):].strip()
            if query:
                return {"action": "web_search", "target": query}
    return None


def _route_system(command: str):
    if command in (
        "вимкни комп", "вимкни комп'ютер", "вимкни пк",
        "выключи компьютер", "выключи пк", "вимкни машину"
    ):
        return {"action": "shutdown", "target": ""}

    if command in (
        "перезавантаж комп", "перезавантаж комп'ютер", "перезавантаж пк",
        "перезапусти пк", "перезагрузи компьютер", "перезагрузи пк", "restart"
    ):
        return {"action": "restart", "target": ""}

    return None


def route(command: str, context=None):
    if not command:
        return None

    normalized = normalize(command)
    if not normalized:
        return None

    # Програма -> сайт -> звук -> музика -> пошук -> система.
    # Discord тепер відкривається як локальна програма, а YouTube залишається сайтом.
    for handler in (
        _route_app,
        _route_site,
        _route_volume,
        _route_music,
        _route_search,
        _route_system,
    ):
        result = handler(normalized)
        if result is not None:
            print(f"[router] LOCAL: {result['action']} -> {result['target']}")
            return result

    print("[router] LOCAL: не визначено")
    return None
