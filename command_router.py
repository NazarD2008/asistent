import re

from tools import apps
from tools import browser


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(text: str) -> str:

    if not text:
        return ""

    text = str(text).lower().strip()

    text = (
        text
        .replace("ё", "е")
        .replace("’", "'")
        .replace("`", "'")
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


# ============================================================
# ACTION WORDS
# ============================================================

OPEN_WORDS = (
    "відкрий",
    "відкрити",
    "відкрив",
    "відкрой",
    "открой",
    "отрой",
    "запусти",
    "запустити",
    "включи",
    "включити",
    "увімкни",
    "увімкнути",
)

CLOSE_WORDS = (
    "закрий",
    "закрити",
    "закрой",
    "закрыть",
    "вимкни",
    "вимкнути",
)


# ============================================================
# FIND APP
# ============================================================

def _find_app(command: str):

    aliases = sorted(
        apps.APP_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for phrase, app_name in aliases:

        if phrase in command:
            return app_name

    return None


# ============================================================
# APP ROUTER
# ============================================================

def _route_app(command: str):

    app_name = _find_app(command)

    if not app_name:
        return None

    # --------------------------------------------------------
    # CLOSE
    # --------------------------------------------------------

    for word in CLOSE_WORDS:

        if (
            command.startswith(word + " ")
            or command == word
        ):

            return {
                "action": "close_app",
                "target": app_name,
            }

    # --------------------------------------------------------
    # OPEN
    # --------------------------------------------------------

    for word in OPEN_WORDS:

        if (
            command.startswith(word + " ")
            or command == word
        ):

            return {
                "action": "open_app",
                "target": app_name,
            }

    return None


# ============================================================
# GOOGLE / URL
# ============================================================

def _route_url(command: str):

    google_words = (
        "гугл",
        "google",
        "google.com",
    )

    if not any(word in command for word in google_words):
        return None

    # Не перехоплюємо пошукові запити.
    search_words = (
        "знайди",
        "знайти",
        "пошукай",
        "пошук",
        "погода",
        "новини",
        "курс",
    )

    if any(word in command for word in search_words):
        return None

    if command in (
        "відкрий гугл",
        "відкрити гугл",
        "запусти гугл",
        "відкрий google",
        "відкрити google",
        "запусти google",
    ):

        return {
            "action": "open_url",
            "target": "https://www.google.com",
        }

    return None


# ============================================================
# VOLUME
# ============================================================

def _route_volume(command: str):

    # --------------------------------------------------------
    # SET VOLUME
    # --------------------------------------------------------

    match = re.search(
        r"(?:звук|гучність|громкость)"
        r"\s*(?:на|до)?\s*(\d{1,3})",
        command,
    )

    if match:

        percent = int(match.group(1))

        percent = max(
            0,
            min(100, percent),
        )

        return {
            "action": "set_volume",
            "target": str(percent),
        }

    # --------------------------------------------------------
    # VOLUME UP
    # --------------------------------------------------------

    if any(
        phrase in command
        for phrase in (
            "зроби голосніше",
            "зроби гучніше",
            "збільш звук",
            "додай гучності",
            "прибавь звук",
            "голосніше",
            "гучніше",
        )
    ):

        return {
            "action": "volume_up",
            "target": "",
        }

    # --------------------------------------------------------
    # VOLUME DOWN
    # --------------------------------------------------------

    if any(
        phrase in command
        for phrase in (
            "зроби тихіше",
            "зменш звук",
            "зменш гучність",
            "прибери гучність",
            "убавь звук",
            "тихіше",
        )
    ):

        return {
            "action": "volume_down",
            "target": "",
        }

    # --------------------------------------------------------
    # MUTE
    # --------------------------------------------------------

    if any(
        phrase in command
        for phrase in (
            "вимкни звук",
            "выключи звук",
            "заглуши звук",
            "приглуши звук",
            "mute",
        )
    ):

        return {
            "action": "mute",
            "target": "",
        }

    # --------------------------------------------------------
    # UNMUTE
    # --------------------------------------------------------

    if any(
        phrase in command
        for phrase in (
            "увімкни звук",
            "включи звук",
            "поверни звук",
            "unmute",
        )
    ):

        return {
            "action": "unmute",
            "target": "",
        }

    return None


# ============================================================
# SYSTEM
# ============================================================

def _route_system(command: str):

    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------

    if command in (
        "вимкни комп",
        "вимкни комп'ютер",
        "вимкни пк",
        "выключи компьютер",
        "выключи пк",
        "вимкни машину",
    ):

        return {
            "action": "shutdown",
            "target": "",
        }

    # --------------------------------------------------------
    # RESTART
    # --------------------------------------------------------

    if command in (
        "перезавантаж комп",
        "перезавантаж комп'ютер",
        "перезавантаж пк",
        "перезапусти пк",
        "перезагрузи компьютер",
        "перезагрузи пк",
        "restart",
    ):

        return {
            "action": "restart",
            "target": "",
        }

    return None


# ============================================================
# MAIN ROUTER
# ============================================================

def route(command: str, context=None):
    """
    Локальний маршрутизатор.

    Router НЕ виконує інструменти.
    Він лише визначає просту команду і повертає:

        {
            "action": "...",
            "target": "..."
        }

    Якщо команда не визначена локально:
        повертає None.

    GPT тут НІКОЛИ не викликається.
    """

    if not command:
        return None

    normalized = normalize(command)

    if not normalized:
        return None

    # ========================================================
    # 1. PROGRAMS
    # ========================================================

    result = _route_app(normalized)

    if result is not None:
        print(
            f"[router] LOCAL: "
            f"{result['action']} -> "
            f"{result['target']}"
        )
        return result

    # ========================================================
    # 2. GOOGLE
    # ========================================================

    result = _route_url(normalized)

    if result is not None:
        print(
            f"[router] LOCAL: "
            f"{result['action']} -> "
            f"{result['target']}"
        )
        return result

    # ========================================================
    # 3. VOLUME
    # ========================================================

    result = _route_volume(normalized)

    if result is not None:
        print(
            f"[router] LOCAL: "
            f"{result['action']} -> "
            f"{result['target']}"
        )
        return result

    # ========================================================
    # 4. SYSTEM
    # ========================================================

    result = _route_system(normalized)

    if result is not None:
        print(
            f"[router] LOCAL: "
            f"{result['action']} -> "
            f"{result['target']}"
        )
        return result

    print(
        "[router] LOCAL: не визначено"
    )

    return None