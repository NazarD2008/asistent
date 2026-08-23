"""
JARVIS Brain

Відповідає за:
- розуміння складних команд через GPT;
- визначення action / target;
- виконання action;
- YouTube;
- фільми;
- web search;
- системні команди.

ВАЖЛИВО:

Локальні прості команди обробляються command_router.py.

Brain НЕ має другого локального parser'а.

GPT викликається максимум один раз на команду.
"""

import os
import json

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# ENV
# ============================================================

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY"
)

AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT"
)

AZURE_OPENAI_MODEL = os.getenv(
    "AZURE_OPENAI_MODEL",
    "gpt-5-mini"
)


# ============================================================
# OPENAI CLIENT
# ============================================================

client = None

if (
    AZURE_OPENAI_API_KEY
    and AZURE_OPENAI_ENDPOINT
):

    try:

        client = OpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            base_url=AZURE_OPENAI_ENDPOINT,
        )

        print(
            "[brain] OpenAI client готовий."
        )

    except Exception as e:

        print(
            f"[brain] Помилка створення OpenAI client: {e}"
        )


# ============================================================
# TOOLS
# ============================================================

from tools import browser
from tools import apps


# ============================================================
# ALLOWED ACTIONS
# ============================================================

ALLOWED_ACTIONS = {
    "open_app",
    "close_app",

    "play_music",
    "play_video",
    "open_video_result",

    "find_movie",

    "open_url",
    "web_search",

    "delete_file",
    "analyze_memory",

    "set_volume",
    "volume_up",
    "volume_down",
    "mute",
    "unmute",

    "shutdown",
    "restart",

    "stop",

    "chat",

    "unknown",
}


# ============================================================
# LAST PARSED
# ============================================================

_last_action = None
_last_target = None


def get_last_parsed():
    """
    Повертає action / target останнього GPT-парсингу.

    Використовується Agent для пам'яті.
    """

    return (
        _last_action,
        _last_target,
    )


# ============================================================
# GPT PARSER
# ============================================================

def _parse_command(
    command: str,
    context=None,
):
    """
    Передає складну команду GPT.

    GPT повертає тільки:

    {
        "action": "...",
        "target": "..."
    }
    """

    if not client:

        print(
            "[brain] OpenAI client недоступний."
        )

        return {
            "action": "unknown",
            "target": "",
        }

    if context is None:
        context = []

    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    system_prompt = """
Ти мозок голосового асистента JARVIS.

Твоє завдання:
визначити намір користувача та перетворити команду
на JSON.

ПОВЕРТАЙ ТІЛЬКИ JSON.

Без markdown.
Без пояснень.
Без тексту до або після JSON.

Формат:

{
  "action": "ACTION",
  "target": "TARGET"
}

Дозволені action:

open_app
close_app

play_music
play_video
open_video_result

find_movie

open_url
web_search

delete_file
analyze_memory

set_volume
volume_up
volume_down
mute
unmute

shutdown
restart

stop
chat
unknown


============================================================
ВІДКРИТТЯ ПРОГРАМ
============================================================

Якщо користувач хоче відкрити програму:

"відкрий Steam"
"запусти Chrome"
"включи Discord"

→

{
  "action": "open_app",
  "target": "steam"
}

або відповідну назву програми.


============================================================
ЗАКРИТТЯ ПРОГРАМ
============================================================

Якщо користувач хоче закрити програму:

"закрий Steam"
"закрий Chrome"

→

{
  "action": "close_app",
  "target": "steam"
}


============================================================
YOUTUBE
============================================================

Якщо користувач просить знайти відео:

"знайди відео про космос"
"пошукай Рік і Морті на YouTube"
"включи відео про Minecraft"

→

{
  "action": "play_video",
  "target": "пошуковий запит"
}


ВАЖЛИВО:

Назва серіалу, мультсеріалу, фільму або шоу
НЕ означає автоматично YouTube.

Наприклад:

"включи Рік і Морті"

НЕ треба автоматично перетворювати на:

play_video

Якщо користувач просто називає фільм або серіал,
використовуй:

find_movie

або chat,

залежно від контексту.

Якщо користувач явно говорить:

"знайди на YouTube"
"пошукай на YouTube"
"відкрий на YouTube"
"включи на YouTube"

тоді:

play_video


============================================================
ВИБІР YOUTUBE РЕЗУЛЬТАТУ
============================================================

Якщо в контексті видно, що перед цим JARVIS
знайшов YouTube-результати, тоді:

"перше"
"перше відео"
"відкрий перше"
"відкрий 1"
"запусти друге"
"третє"

→

{
  "action": "open_video_result",
  "target": "номер"
}


НЕ ВИГАДУЙ номер.

Використовуй номер тільки якщо користувач його
явно назвав або контекст однозначно показує,
що він вибирає результат.


============================================================
МУЗИКА
============================================================

Якщо користувач хоче просто відкрити/включити
музику:

"включи музику"
"постав музику"

→

{
  "action": "play_music",
  "target": ""
}


Якщо користувач просить конкретну музику:

"включи Imagine Dragons"
"постав музику Eminem"

→

{
  "action": "play_music",
  "target": "Imagine Dragons"
}


============================================================
ФІЛЬМИ / СЕРІАЛИ
============================================================

Якщо користувач просить знайти фільм або серіал:

"знайди Інтерстеллар"
"знайди фільм Інтерстеллар"
"де подивитися Рік і Морті"

→

{
  "action": "find_movie",
  "target": "Інтерстеллар"
}

або назву відповідного фільму/серіалу.


ВАЖЛИВО:

Не додавай до target службові слова:

"знайди"
"знайде"
"знайти"
"фільм"
"фильм"
"серіал"

якщо вони не є частиною назви.


Наприклад:

"знайде фільм Інтерстел"

→

{
  "action": "find_movie",
  "target": "Інтерстел"
}


============================================================
WEB SEARCH
============================================================

Якщо користувач питає про інформацію,
яку треба отримати з інтернету:

курс валют
погода
новини
актуальні ціни
актуальна інформація про людей
поточні події

→

{
  "action": "web_search",
  "target": "пошуковий запит"
}


============================================================
SHUTDOWN / RESTART
============================================================

shutdown використовуй ТІЛЬКИ якщо користувач
явно просить вимкнути комп'ютер.

Наприклад:

"вимкни комп'ютер"
"вимкни ПК"

→ shutdown


restart використовуй ТІЛЬКИ якщо користувач
явно просить перезавантажити ПК.

Наприклад:

"перезавантаж комп'ютер"
"перезапусти ПК"

→ restart


ВАЖЛИВО:

"стоп"
"вихід"
"досить"
"закінчуй"

це:

{
  "action": "stop",
  "target": ""
}

а НЕ shutdown.


============================================================
CHAT
============================================================

Якщо користувач просто спілкується:

"привіт"
"як справи?"
"розкажи про чорні діри"
"дякую"

→

{
  "action": "chat",
  "target": "коротка природна відповідь"
}


Для chat:

- українська мова;
- 2-4 речення;
- без markdown;
- без списків;
- без емодзі;
- відповідь призначена для TTS;
- говори природно;
- не вигадуй факти.


============================================================
КОНТЕКСТ
============================================================

Використовуй передану історію команд.

Контекст може містити:

- попередню команду;
- відповідь;
- action;
- target;
- час.

Не вигадуй контекст.

Якщо попередня команда була:

"знайди відео про Рік і Морті"

а наступна:

"відкрий перше"

тоді:

{
  "action": "open_video_result",
  "target": "1"
}


============================================================
TARGET
============================================================

target ЗАВЖДИ має бути рядком.

Для action-команд:

target має бути коротким і чистим.

Для chat:

target є повною відповіддю JARVIS.
"""


    # ========================================================
    # USER INPUT
    # ========================================================

    user_content = {
        "command": command,
        "context": context,
    }

    try:

        response = client.responses.create(
            model=AZURE_OPENAI_MODEL,
            instructions=system_prompt,
            input=json.dumps(
                user_content,
                ensure_ascii=False,
            ),
        )

        raw = response.output_text.strip()

        print(
            f"[brain] GPT raw: {raw}"
        )

        # ====================================================
        # JSON
        # ====================================================

        try:

            data = json.loads(raw)

        except json.JSONDecodeError:

            cleaned = raw

            cleaned = cleaned.replace(
                "```json",
                "",
            )

            cleaned = cleaned.replace(
                "```",
                "",
            )

            cleaned = cleaned.strip()

            data = json.loads(
                cleaned
            )

        action = data.get(
            "action",
            "unknown",
        )

        target = data.get(
            "target",
            "",
        )

        if action not in ALLOWED_ACTIONS:

            action = "unknown"

        return {
            "action": action,
            "target": str(target).strip(),
        }

    except Exception as e:

        print(
            f"[brain] GPT parser error: {e}"
        )

        return {
            "action": "unknown",
            "target": "",
        }


# ============================================================
# YOUTUBE SHORT RESPONSE
# ============================================================

def _youtube_short_response(
    target: str,
) -> str:

    results = browser.get_last_results()

    if not results:

        return (
            f"Шукаю відео про {target}."
        )

    return (
        f"Знайшов {len(results)} відео. "
        f"Яке відкрити?"
    )


# ============================================================
# EXECUTE ACTION
# ============================================================

def execute(
    action: str,
    target: str,
    command: str = "",
) -> str:

    action = action or "unknown"
    target = target or ""

    print(
        f"[brain] Execute: {action}"
    )

    print(
        f"[brain] Target: {target}"
    )


    # ========================================================
    # OPEN APP
    # ========================================================

    if action == "open_app":

        return apps.open_app(
            target
        )


    # ========================================================
    # CLOSE APP
    # ========================================================

    if action == "close_app":

        return apps.close_app(
            target
        )


    # ========================================================
    # VIDEO SEARCH
    # ========================================================

    if action == "play_video":

        result = browser.play_video(
            target
        )

        if browser.has_last_results():

            return _youtube_short_response(
                target
            )

        return result


    # ========================================================
    # OPEN VIDEO RESULT
    # ========================================================

    if action == "open_video_result":

        try:

            number = int(
                str(target).strip()
            )

        except Exception:

            return (
                "Не зрозумів номер відео."
            )

        result = browser.open_video_number(
            number
        )

        if browser.has_last_results():

            browser.clear_last_results()

        return result


    # ========================================================
    # MUSIC
    # ========================================================

    if action == "play_music":

        return browser.play_music(
            target
        )


    # ========================================================
    # MOVIE / SERIES
    # ========================================================

    if action == "find_movie":

        return browser.find_movie(
            target
        )


    # ========================================================
    # URL
    # ========================================================

    if action == "open_url":

        return browser.open_url(
            target
        )


    # ========================================================
    # WEB SEARCH
    # ========================================================

    if action == "web_search":

        if not target:

            return (
                "Не вказаний пошуковий запит."
            )

        try:

            search_url = (
                "https://www.google.com/search?q="
                + target.replace(" ", "+")
            )

            print(
                f"[brain] Web search: {search_url}"
            )

            browser.open_url(
                search_url
            )

            return (
                f"Шукаю результати для {target}."
            )

        except Exception as e:

            print(
                f"[brain] Web search error: {e}"
            )

            return (
                "Не вдалося виконати пошук."
            )


    # ========================================================
    # MEMORY
    # ========================================================

    if action == "analyze_memory":

        try:

            from disk_analyzer import analyze_memory

            return str(
                analyze_memory()
            )

        except Exception as e:

            print(
                f"[brain] Memory error: {e}"
            )

            return (
                "Не вдалося проаналізувати "
                "пам'ять комп'ютера."
            )


    # ========================================================
    # VOLUME
    # ========================================================

    if action in (
        "set_volume",
        "volume_up",
        "volume_down",
        "mute",
        "unmute",
    ):

        try:

            from tools import system

            function = getattr(
                system,
                action,
            )

            if target:

                return str(
                    function(target)
                )

            return str(
                function()
            )

        except Exception as e:

            print(
                f"[brain] Volume error: {e}"
            )

            return (
                "Не вдалося змінити гучність."
            )


    # ========================================================
    # SHUTDOWN
    # ========================================================

    if action == "shutdown":

        try:

            from tools import system
            from permissions import ActionCancelled

            return system.shutdown()

        except ActionCancelled:

            return "Добре, скасовано."

        except Exception as e:

            print(
                f"[brain] Shutdown error: {e}"
            )

            return (
                "Не вдалося вимкнути комп'ютер."
            )


    # ========================================================
    # RESTART
    # ========================================================

    if action == "restart":

        try:

            from tools import system
            from permissions import ActionCancelled

            return system.restart()

        except ActionCancelled:

            return "Добре, скасовано."

        except Exception as e:

            print(
                f"[brain] Restart error: {e}"
            )

            return (
                "Не вдалося перезавантажити комп'ютер."
            )


    # ========================================================
    # CHAT
    # ========================================================

    if action == "chat":

        if not target:

            return "Так, слухаю."

        return target


    # ========================================================
    # STOP
    # ========================================================

    if action == "stop":

        return "До зустрічі."


    # ========================================================
    # UNKNOWN
    # ========================================================

    return (
        "Не зовсім зрозумів команду."
    )


# ============================================================
# HANDLE
# ============================================================

def handle(
    command: str,
    context=None,
) -> str:

    global _last_action
    global _last_target

    if not command or not command.strip():

        _last_action = None
        _last_target = None

        return (
            "Я не почув команду."
        )

    command = command.strip()

    if context is None:
        context = []

    print(
        "[brain] Передаю команду GPT..."
    )

    # ========================================================
    # GPT
    # ========================================================

    parsed = _parse_command(
        command,
        context=context,
    )

    action = parsed.get(
        "action",
        "unknown",
    )

    target = parsed.get(
        "target",
        "",
    )

    _last_action = action
    _last_target = target

    print(
        f"[brain] GPT ACTION: "
        f"{action} -> {target}"
    )

    return execute(
        action,
        target,
        command,
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "=" * 60
    )

    print(
        "JARVIS BRAIN TEST"
    )

    print(
        "=" * 60
    )

    while True:

        command = input(
            "\nJARVIS > "
        ).strip()

        if not command:
            continue

        if command.lower() in (
            "exit",
            "quit",
            "стоп",
        ):

            break

        print(
            handle(command)
        )