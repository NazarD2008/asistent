"""
JARVIS Brain

Відповідає ТІЛЬКИ за розуміння складних команд через GPT.

Brain:
- отримує команду та контекст;
- визначає action / target;
- повертає структуроване рішення.

Brain НЕ виконує tools.
Виконання знаходиться в agent.py.
"""

import json
import os

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
    "gpt-5-mini",
)


# ============================================================
# OPENAI CLIENT
# ============================================================

client = None

if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:

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

    system_prompt = """
Ти мозок голосового асистента JARVIS.

Твоє завдання: визначити НАМІР користувача та повернути
структуровану команду для Agent.

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
ЗАГАЛЬНИЙ ПРИНЦИП
============================================================

Не орієнтуйся на окремі ключові слова.
Визначай намір з урахуванням усієї фрази та context.

Не вигадуй параметри, яких користувач не сказав.

target ЗАВЖДИ рядок.

============================================================
ПРОГРАМИ
============================================================

"відкрий Steam"
"запусти Chrome"
"включи Discord"

→ action = open_app
→ target = назва програми

"закрий Steam"
"закрий Chrome"

→ action = close_app
→ target = назва програми

============================================================
МУЗИКА
============================================================

"включи музику"
→ play_music, target = ""

"включи Imagine Dragons"
→ play_music, target = "Imagine Dragons"

============================================================
YOUTUBE / ВІДЕО
============================================================

Використовуй play_video ТІЛЬКИ коли користувач явно просить
відео або явно вказує YouTube як джерело.

Приклади:
"знайди відео про космос"
"пошукай це на YouTube"
"відкрий Рік і Морті на YouTube"

→ play_video

Назва фільму, серіалу, шоу або гри сама по собі
НЕ означає YouTube.

============================================================
ФІЛЬМИ / СЕРІАЛИ / КОНТЕНТ
============================================================

Не створюй окремі правила для конкретних назв.
Це правило однаково працює для будь-якого контенту.

Якщо користувач хоче знайти або подивитися фільм/серіал,
але не вказав платформу:

→ find_movie
→ target = назва контенту

Приклади:
"знайди Інтерстеллар"
"хочу подивитися Рік і Морті"
"де подивитися Breaking Bad"

Якщо користувач явно вказує YouTube:
→ play_video

============================================================
YOUTUBE РЕЗУЛЬТАТИ
============================================================

Якщо context показує, що попередньо був список YouTube
результатів, тоді команди:

"перше"
"друге"
"третє"
"відкрий перше"
"відкрий 2"

→ open_video_result
→ target = номер

Не вигадуй номер.

============================================================
WEB SEARCH
============================================================

Якщо користувач просить актуальну інформацію:

курс валют
погода
новини
актуальні ціни
поточні події
актуальна інформація про людей

→ web_search
→ target = пошуковий запит

============================================================
SYSTEM
============================================================

shutdown ТІЛЬКИ для явного вимкнення ПК.

restart ТІЛЬКИ для явного перезавантаження ПК.

"стоп", "вихід", "досить", "закінчуй"
→ stop

============================================================
CHAT
============================================================

Звичайне спілкування:
"привіт"
"як справи?"
"поясни що таке Python"

→ chat
→ target = готова природна відповідь українською.

Відповідь для TTS:
- без markdown;
- без списків;
- без емодзі;
- зазвичай 2-4 речення.

============================================================
CONTEXT
============================================================

Використовуй context для розуміння:
- "це"
- "його"
- "другий"
- "відкрий перший"
- "на YouTube"
- інших follow-up команд.

Наприклад:

Попередня команда:
"знайди відео про Python"

Нова команда:
"друге"

→ open_video_result, target = "2"

Не вважай попередню команду поточною дією.
Використовуй її лише для розуміння нової команди.
"""

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

        try:

            data = json.loads(raw)

        except json.JSONDecodeError:

            cleaned = raw.replace(
                "```json",
                "",
            ).replace(
                "```",
                "",
            ).strip()

            data = json.loads(cleaned)

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
# HANDLE
# ============================================================

def handle(
    command: str,
    context=None,
):
    """
    Розуміє команду через GPT.

    ВАЖЛИВО:
    handle() НЕ виконує tools.
    Він повертає dict:

    {
        "action": "...",
        "target": "..."
    }
    """

    global _last_action
    global _last_target

    if not command or not command.strip():

        _last_action = None
        _last_target = None

        return {
            "action": "unknown",
            "target": "",
        }

    command = command.strip()

    if context is None:
        context = []

    print(
        "[brain] Передаю команду GPT..."
    )

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
        f"[brain] Intent: {action}"
    )

    print(
        f"[brain] Target: {target}"
    )

    return {
        "action": action,
        "target": target,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("JARVIS BRAIN TEST")
    print("=" * 60)

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
