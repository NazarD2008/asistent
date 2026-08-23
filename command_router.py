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
    "відкрий", "відкрити", "відкрив", "відкрой", "відкрйи",
    "открой", "отрой", "запусти", "запустити", "включи",
    "включити", "увімкни", "увімкнути",
)

CLOSE_WORDS = (
    "закрий", "закрити", "закрой", "закрыть", "вимкни", "вимкнути",
)


def _find_app(command: str):
    aliases = sorted(apps.APP_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
    for phrase, app_name in aliases:
        if phrase in command:
            return app_name
    return None


def _route_app(command: str):
    app_name = _find_app(command)
    if not app_name:
        return None

    if any(command == word or command.startswith(word + " ") for word in CLOSE_WORDS):
        return {"action": "close_app", "target": app_name}

    if any(command == word or command.startswith(word + " ") for word in OPEN_WORDS):
        return {"action": "open_app", "target": app_name}

    return None


def _route_youtube(command: str):
    youtube_words = ("youtube", "ютуб", "ютюб", "ю туб")
    if not any(word in command for word in youtube_words):
        return None

    if any(word in command for word in CLOSE_WORDS):
        return None

    if any(word in command for word in OPEN_WORDS):
        return {"action": "open_url", "target": "https://www.youtube.com"}

    return None


def _route_url(command: str):
    google_words = ("гугл", "google", "google.com")
    if not any(word in command for word in google_words):
        return None

    search_words = ("знайди", "знайти", "пошукай", "пошук", "погода", "новини", "курс")
    if any(word in command for word in search_words):
        return None

    if command in (
        "відкрий гугл", "відкрити гугл", "запусти гугл",
        "відкрий google", "відкрити google", "запусти google",
    ):
        return {"action": "open_url", "target": "https://www.google.com"}

    return None


def _route_volume(command: str):
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


def _route_system(command: str):
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

    # Порядок важливий: YouTube є сайтом, а не локальною програмою.
    result = _route_youtube(normalized)
    if result is not None:
        print(f"[router] LOCAL: {result['action']} -> {result['target']}")
        return result

    result = _route_app(normalized)
    if result is not None:
        print(f"[router] LOCAL: {result['action']} -> {result['target']}")
        return result

    result = _route_url(normalized)
    if result is not None:
        print(f"[router] LOCAL: {result['action']} -> {result['target']}")
        return result

    result = _route_volume(normalized)
    if result is not None:
        print(f"[router] LOCAL: {result['action']} -> {result['target']}")
        return result

    result = _route_system(normalized)
    if result is not None:
        print(f"[router] LOCAL: {result['action']} -> {result['target']}")
        return result

    print("[router] LOCAL: не визначено")
    return None
