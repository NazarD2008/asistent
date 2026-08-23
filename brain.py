"""
JARVIS Brain

Мозок JARVIS.

Відповідає за:
- локальний парсинг простих команд;
- GPT-парсинг складних команд;
- виконання action;
- YouTube;
- відкриття конкретного відео;
- програми Windows;
- пам'ять контексту;
- короткі відповіді для TTS.

ВАЖЛИВО:
- Не імпортує KNOWN_APPS.
- Працює з реальним tools.apps.py.
- Не робить подвійний GPT-запит.
- Команди вибору YouTube обробляються локально.
"""

import os
import json
import re

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
# LAST PARSED (для agent.py, щоб уникнути подвійного GPT-запиту)
# ============================================================

_last_action = None
_last_target = None


def get_last_parsed():
    """
    Повертає (action, target) з останнього виклику handle().
    Потрібно, щоб agent.py міг зберегти action/target у пам'ять
    БЕЗ повторного виклику GPT.
    """

    return _last_action, _last_target


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
    "web_search",
    "unknown",
}

# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(text: str) -> str:

    if not text:
        return ""

    return (
        str(text)
        .lower()
        .strip()
        .replace("ё", "е")
        .replace("’", "'")
        .replace("`", "'")
    )


# ============================================================
# NUMBER PARSER
# ============================================================

def _extract_number(text: str):

    """
    Розуміє:

    1
    2
    3
    перше
    перший
    першу
    друге
    другий
    третє
    третій
    четверте
    четвертий
    п'яте
    п'ятий
    """

    text = _normalize(text)

    # --------------------------------------------------------
    # Цифра
    # --------------------------------------------------------

    match = re.search(
        r"\b([1-9]|10)\b",
        text
    )

    if match:

        return int(
            match.group(1)
        )

    # --------------------------------------------------------
    # Українські / російські слова
    # --------------------------------------------------------

    numbers = {

        "перше": 1,
        "перший": 1,
        "першу": 1,
        "первое": 1,
        "первый": 1,
        "первую": 1,

        "друге": 2,
        "другий": 2,
        "другу": 2,
        "второе": 2,
        "второй": 2,
        "вторую": 2,

        "третє": 3,
        "третій": 3,
        "третю": 3,
        "третье": 3,
        "третий": 3,
        "третью": 3,

        "четверте": 4,
        "четвертий": 4,
        "четверту": 4,
        "четвертое": 4,
        "четвертый": 4,
        "четвертую": 4,

        "п'яте": 5,
        "п'ятий": 5,
        "п'яту": 5,
        "пятое": 5,
        "пятый": 5,
        "пятую": 5,

        "шосте": 6,
        "шостий": 6,
        "шосту": 6,
        "шестое": 6,
        "шестой": 6,
        "шестую": 6,

        "сьоме": 7,
        "сьомий": 7,
        "сьому": 7,
        "седьмое": 7,
        "седьмой": 7,
        "седьмую": 7,

        "восьме": 8,
        "восьмий": 8,
        "восьму": 8,
        "восьмое": 8,
        "восьмой": 8,
        "восьмую": 8,

        "дев'яте": 9,
        "дев'ятий": 9,
        "дев'яту": 9,
        "девятое": 9,
        "девятый": 9,
        "девятую": 9,

        "десяте": 10,
        "десятий": 10,
        "десяту": 10,
        "десятое": 10,
        "десятый": 10,
        "десятую": 10,
    }

    words = text.split()

    for word in words:

        clean = word.strip(
            ".,!?;:()[]{}"
        )

        if clean in numbers:

            return numbers[clean]

    # --------------------------------------------------------
    # Варіант "номер перший"
    # --------------------------------------------------------

    for word, number in numbers.items():

        if word in text:

            return number

    return None


# ============================================================
# LOCAL PARSER
# ============================================================

def _local_parse(command: str):
    """
    Локальний parser.

    Тут НЕ виконується команда.
    Він тільки визначає action / target.
    """

    if not command:
        return None

    text = _normalize(command)

    # ========================================================
    # STOP
    # ========================================================

    if text in (
            "стоп",
            "вихід",
            "вийти",
            "exit",
            "quit",
    ):
        return {
            "action": "stop",
            "target": ""
        }
    # ========================================================
    # YOUTUBE RESULT
    # ========================================================

    # Це повинно перевірятися ПЕРШИМ.
    #
    # "відкрий 1"
    # "відкрий перше"
    # "перше відео"
    # "відкрий третє відео"

    number = _extract_number(text)

    youtube_result_words = (
        "відео",
        "ролик",
        "результат",
    )

    if number is not None:

        if (
            "відкрий" in text
            or "відкрити" in text
            or "запусти" in text
            or "запустити" in text
            or "покажи" in text
            or "покажи" in text
            or any(
                word in text
                for word in youtube_result_words
            )
        ):

            if browser.has_last_results():

                return {
                    "action": "open_video_result",
                    "target": str(number)
                }

    # ========================================================
    # OPEN APP
    # ========================================================

    open_words = (
        "відкрий",
        "відкрити",
        "запусти",
        "запустити",
        "включи",
        "включити",
        "відкрив",
    )

    if any(
        word in text
        for word in open_words
    ):

        # ----------------------------------------------------
        # Якщо є активний YouTube список
        # ----------------------------------------------------

        if browser.has_last_results():

            number = _extract_number(text)

            if number is not None:

                return {
                    "action": "open_video_result",
                    "target": str(number)
                }

        # ----------------------------------------------------
        # Програми
        # ----------------------------------------------------

        app_aliases = apps.APP_ALIASES

        # Спочатку найдовші alias
        # щоб "гугл хром" не перетворився
        # на щось неправильне.

        aliases = sorted(
            app_aliases.keys(),
            key=len,
            reverse=True
        )

        for alias in aliases:

            if alias in text:

                return {
                    "action": "open_app",
                    "target": app_aliases[alias]
                }

    # ========================================================
    # CLOSE APP
    # ========================================================

    close_words = (
        "закрий",
        "закрити",
        "вимкни",
        "вимкнути",
    )

    if any(
        word in text
        for word in close_words
    ):

        aliases = sorted(
            apps.APP_ALIASES.keys(),
            key=len,
            reverse=True
        )

        for alias in aliases:

            if alias in text:

                return {
                    "action": "close_app",
                    "target": apps.APP_ALIASES[alias]
                }

    # ========================================================
    # MUSIC
    # ========================================================

    if "музик" in text:

        if any(
            word in text
            for word in (
                "знайди",
                "знайти",
                "включи",
                "включити",
                "постав",
                "поставити",
            )
        ):

            target = text

            for phrase in (
                "знайди музику",
                "знайти музику",
                "включи музику",
                "включити музику",
                "постав музику",
                "поставити музику",
            ):

                target = target.replace(
                    phrase,
                    ""
                )

            return {
                "action": "play_music",
                "target": target.strip()
            }

    # ========================================================
    # VIDEO SEARCH
    # ========================================================

    if "відео" in text:

        if any(
            word in text
            for word in (
                "знайди",
                "знайде",
                "знайти",
                "пошукай",
                "пошук",
                "ютуб",
                "youtube",
            )
        ):

            target = text

            phrases = (
                "знайди відео",
                "знайде відео",
                "знайти відео",
                "пошукай відео",
                "пошук відео",
                "відео на ютубі",
                "відео на youtube",
                "ютуб",
                "youtube",
            )

            for phrase in phrases:

                target = target.replace(
                    phrase,
                    ""
                )

            target = target.strip()

            return {
                "action": "play_video",
                "target": target
            }

    # ========================================================
    # MOVIE
    # ========================================================

    if (
            "фільм" in text
            or "фильм" in text
    ):

        target = text

        phrases = (
            "знайди фільм",
            "знайде фільм",
            "знайти фільм",
            "пошукай фільм",
            "пошук фільму",

            "знайди фильм",
            "знайде фильм",
            "знайти фильм",
            "пошукай фильм",
            "пошук фильма",

            "фільм",
            "фильм",
        )

        for phrase in phrases:
            target = target.replace(
                phrase,
                ""
            )

        target = target.strip()

        if not target:
            target = "популярні фільми"

        return {
            "action": "find_movie",
            "target": target
        }
    return None


# ============================================================
# GPT PARSER
# ============================================================

def _parse_command(
    command: str,
    context=None
):
    """
    Передає складну команду GPT.

    GPT повертає ТІЛЬКИ JSON.
    """

    if not client:

        print(
            "[brain] OpenAI client недоступний."
        )

        return {
            "action": "unknown",
            "target": ""
        }

    if context is None:

        context = []

    system_prompt = """
Ти мозок голосового асистента JARVIS.

Твоє завдання:
перетворити команду користувача на JSON.

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
web_search
unknown

ВАЖЛИВІ ПРАВИЛА:

1. Якщо користувач просить знайти відео:
   action = "play_video"

2. Якщо користувач вибирає номер відео:
   action = "open_video_result"
   target = номер

3. Якщо користувач каже:
   "перше"
   "перше відео"
   "відкрий перше"
   "відкрий 1"
   "запусти 1"

   і контекст показує, що перед цим були результати YouTube,
   використовуй:
   action = "open_video_result"
   target = "1"

4. Не вигадуй номер відео.

5. Для відкриття програм:
   action = "open_app"

6. Дію "shutdown"/"restart" використовуй ТІЛЬКИ якщо користувач
   явно і недвозначно просить вимкнути/перезавантажити комп'ютер
   ("вимкни комп'ютер", "перезавантаж пк").
   Якщо користувач просто хоче завершити розмову
   ("стоп", "вихід", "досить", "закінчуй") — це action = "stop",
   а НЕ "shutdown".

7. Якщо команда НЕ відповідає жодній дії вище — тобто це просто
   розмова, питання, прохання щось пояснити, порада, жарт
   і подібне — використовуй:

   action = "chat"
   target = твоя природна відповідь українською мовою.

   Правила для "chat":
   - Відповідай як JARVIS: впевнено, дружньо, трохи з гумором,
     по суті, від першої особи.
   - Відповідь буде озвучена вголос (TTS), тому:
     без markdown, без списків, без зірочок, без емодзі;
     2-4 речення, якщо користувач не просив детальнішу відповідь.
   - Використовуй "context" (історію попередніх команд/реплік),
     щоб пам'ятати, про що йшла розмова, і відповідати з огляду
     на це.
   - Якщо не знаєш відповіді напевно — чесно скажи, що не
     впевнений, замість вигадувати факти.

8. Якщо користувач питає про курс валют, погоду, новини, 
   ціни товарів, інформацію про людей — використовуй:
   action = "web_search"
   target = пошуковий запит (українською або англійською)
   
   Приклади:
   - "курс долара" → web_search: "курс долара НБУ"
   - "яка погода" → web_search: "погода Київ"
   - "новини" → web_search: "новини України"

9. target завжди рядок. Для дій-команд — короткий і чистий
   (назва програми, номер, пошуковий запит). Для "chat" —
   це і є повний текст відповіді, він може бути довшим.
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
                ensure_ascii=False
            ),
        )

        raw = response.output_text.strip()

        print(
            f"[brain] GPT raw: {raw}"
        )

        # ----------------------------------------------------
        # JSON
        # ----------------------------------------------------

        try:

            data = json.loads(raw)

        except json.JSONDecodeError:

            # ------------------------------------------------
            # Якщо модель випадково дала markdown
            # ------------------------------------------------

            cleaned = raw

            cleaned = cleaned.replace(
                "```json",
                ""
            )

            cleaned = cleaned.replace(
                "```",
                ""
            )

            cleaned = cleaned.strip()

            data = json.loads(
                cleaned
            )

        action = data.get(
            "action",
            "unknown"
        )

        target = data.get(
            "target",
            ""
        )

        if action not in ALLOWED_ACTIONS:

            action = "unknown"

        return {
            "action": action,
            "target": str(target).strip()
        }

    except Exception as e:

        print(
            f"[brain] GPT parser error: {e}"
        )

        return {
            "action": "unknown",
            "target": ""
        }


# ============================================================
# SHORT YOUTUBE RESPONSE
# ============================================================

def _youtube_short_response(
    target: str
) -> str:

    results = browser.get_last_results()

    if not results:

        return (
            f"Шукаю відео про {target}."
        )

    # ВАЖЛИВО:
    # НЕ озвучуємо всі 5 назв.
    #
    # Інакше Azure TTS читає пів хвилини,
    # а користувач уже встиг сказати "перше".

    return (
        f"Знайшов {len(results)} відео. "
        f"Яке відкрити?"
    )


# ============================================================
# EXECUTE ACTION
# ============================================================

def _execute(
    action: str,
    target: str,
    command: str = ""
) -> str:

    action = action or "unknown"
    target = target or ""

    print(
        f"[brain] Action: {action}"
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

        # Якщо API знайшов результати,
        # повертаємо КОРОТКУ відповідь.

        if browser.has_last_results():

            return _youtube_short_response(
                target
            )

        return result

    # ========================================================
    # OPEN VIDEO RESULT
    # ========================================================

    if action == "open_video_result":

        number = _extract_number(
            str(target)
        )

        if number is None:

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

        # ----------------------------------------------------
        # ВАЖЛИВО:
        # після вибору вимикаємо список
        # ----------------------------------------------------

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
    # CHAT (вільна розмова)
    # ========================================================

    if action == "chat":

        if not target:

            return "Так, слухаю."

        return target
    # ========================================================
    # MOVIE
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

            if hasattr(
                system,
                action
            ):

                function = getattr(
                    system,
                    action
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

            return "Не вдалося вимкнути комп'ютер."

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

            return "Не вдалося перезавантажити комп'ютер."
    # ========================================================
    # WEB SEARCH
    # ========================================================

    if action == "web_search":

        query = target or ""

        if not query:
            return "Не вказаний пошуковий запит."

        try:

            # Формуємо URL для пошуку в Google
            search_url = (
                f"https://www.google.com/search?q={query.replace(' ', '+')}"
            )

            print(
                f"[brain] Відкриваю браузер: {search_url}"
            )

            # Відкриваємо в браузері (за замовчуванням Firefox)
            browser.open_url(search_url)

            # Озвучуємо краткий результат
            result = f"Шукаю результати для '{query}'. Дивись у браузері."

            return result

        except Exception as e:

            print(
                f"[brain] Web search error: {e}"
            )

            return f"Помилка пошуку: {str(e)}"

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
    context=None
) -> str:

    global _last_action, _last_target

    if not command or not command.strip():

        _last_action = None
        _last_target = None

        return (
            "Я не почув команду."
        )

    command = command.strip()

    # ========================================================
    # 1. ЛОКАЛЬНИЙ PARSER
    # ========================================================

    local = _local_parse(
        command
    )

    if local:

        action = local.get(
            "action"
        )

        target = local.get(
            "target",
            ""
        )

        _last_action = action
        _last_target = target

        print(
            f"[brain] LOCAL: "
            f"{action} -> {target}"
        )

        return _execute(
            action,
            target,
            command
        )

    # ========================================================
    # 2. GPT
    # ========================================================

    if context is None:

        context = []

    print(
        "[brain] Передаю команду GPT..."
    )

    parsed = _parse_command(
        command,
        context=context
    )

    action = parsed.get(
        "action",
        "unknown"
    )

    target = parsed.get(
        "target",
        ""
    )

    _last_action = action
    _last_target = target

    return _execute(
        action,
        target,
        command
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