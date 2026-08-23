import re

from tools import apps, system
from tools import browser


# ============================================================
# LAST ROUTE
# ============================================================

_last_action = None
_last_target = None


def get_last_route():
    return _last_action, _last_target


def _set_last_route(action, target=""):
    global _last_action, _last_target

    _last_action = action
    _last_target = str(target).strip()


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

    text = re.sub(r"\s+", " ", text)

    return text


# ============================================================
# ACTION WORDS
# ============================================================

OPEN_WORDS = (
    "відкрий",
    "відкрити",
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
# APP
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


def _route_app(command: str):

    app_name = _find_app(command)

    if not app_name:
        return None

    # CLOSE
    for word in CLOSE_WORDS:

        if command.startswith(word + " ") or command == word:

            print(
                f"[router] Локально: close_app -> {app_name}"
            )

            response = apps.close_app(app_name)

            _set_last_route(
                "close_app",
                app_name
            )

            return response

    # OPEN
    for word in OPEN_WORDS:

        if command.startswith(word + " ") or command == word:

            print(
                f"[router] Локально: open_app -> {app_name}"
            )

            response = apps.open_app(app_name)

            _set_last_route(
                "open_app",
                app_name
            )

            return response

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

    if any(word in command for word in google_words):

        # Не перехоплюємо складні пошукові запити.
        # Наприклад:
        # "знайди в гуглі погоду"
        # має піти в GPT/web_search.

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

        if (
            command in (
                "відкрий гугл",
                "відкрити гугл",
                "запусти гугл",
                "відкрий google",
                "відкрити google",
                "запусти google",
            )
        ):

            print(
                "[router] Локально: open_url -> https://www.google.com"
            )

            response = browser.open_url(
                "https://www.google.com"
            )

            _set_last_route(
                "open_url",
                "https://www.google.com"
            )

            return response

    return None


# ============================================================
# VOLUME
# ============================================================

def _route_volume(command: str):

    match = re.search(
        r"(?:звук|гучність|громкость)"
        r"\s*(?:на|до)?\s*(\d{1,3})",
        command,
    )

    if match:

        percent = int(match.group(1))

        percent = max(
            0,
            min(100, percent)
        )

        print(
            f"[router] Локально: set_volume -> {percent}"
        )

        response = system.set_volume(percent)

        _set_last_route(
            "set_volume",
            percent
        )

        return response

    # UP
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

        print("[router] Локально: volume_up")

        response = system.volume_up()

        _set_last_route(
            "volume_up",
            ""
        )

        return response

    # DOWN
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

        print("[router] Локально: volume_down")

        response = system.volume_down()

        _set_last_route(
            "volume_down",
            ""
        )

        return response

    # MUTE
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

        print("[router] Локально: mute")

        response = system.mute()

        _set_last_route(
            "mute",
            ""
        )

        return response

    # UNMUTE
    if any(
        phrase in command
        for phrase in (
            "увімкни звук",
            "включи звук",
            "поверни звук",
            "unmute",
        )
    ):

        print("[router] Локально: unmute")

        response = system.unmute()

        _set_last_route(
            "unmute",
            ""
        )

        return response

    return None


# ============================================================
# SYSTEM
# ============================================================

def _route_system(command: str):

    # SHUTDOWN
    if command in (
        "вимкни комп",
        "вимкни комп'ютер",
        "вимкни пк",
        "выключи компьютер",
        "выключи пк",
        "вимкни машину",
    ):

        print("[router] Локально: shutdown")

        response = system.shutdown()

        _set_last_route(
            "shutdown",
            ""
        )

        return response

    # RESTART
    if command in (
        "перезавантаж комп",
        "перезавантаж комп'ютер",
        "перезавантаж пк",
        "перезапусти пк",
        "перезагрузи компьютер",
        "перезагрузи пк",
        "restart",
    ):

        print("[router] Локально: restart")

        response = system.restart()

        _set_last_route(
            "restart",
            ""
        )

        return response

    return None


# ============================================================
# MAIN ROUTER
# ============================================================

def route(command: str, context=None):

    global _last_action, _last_target

    _last_action = None
    _last_target = None

    if not command:
        return "Я не почув команду."

    normalized = normalize(command)

    if not normalized:
        return "Я не почув команду."

    # 1. PROGRAMS
    result = _route_app(normalized)

    if result is not None:
        return result

    # 2. GOOGLE
    result = _route_url(normalized)

    if result is not None:
        return result

    # 3. VOLUME
    result = _route_volume(normalized)

    if result is not None:
        return result

    # 4. SYSTEM
    result = _route_system(normalized)

    if result is not None:
        return result

    print(
        "[router] Локально не визначено -> GPT"
    )

    return None