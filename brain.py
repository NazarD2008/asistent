"""
JARVIS Brain

Розуміння складних команд через GPT.
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-5-mini")

client = None

if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
    try:
        client = OpenAI(api_key=AZURE_OPENAI_API_KEY, base_url=AZURE_OPENAI_ENDPOINT)
        print("[brain] OpenAI client готовий.")
    except Exception as e:
        print(f"[brain] Помилка створення OpenAI client: {e}")

ALLOWED_ACTIONS = {
    "open_app", "close_app", "play_music", "play_video",
    "open_video_result", "find_content", "open_url", "web_search",
    "find_file", "open_file", "find_folder", "open_path", "delete_file",
    "analyze_memory", "set_volume", "volume_up", "volume_down", "mute", "unmute",
    "shutdown", "restart", "stop", "chat", "unknown",
}

_last_action = None
_last_target = None


def get_last_parsed():
    return _last_action, _last_target


SYSTEM_PROMPT = """
Ти мозок JARVIS. Твоє завдання: зрозуміти НАМІР користувача та повернути одну дію.
ПОВЕРТАЙ ТІЛЬКИ JSON:
{"action":"ACTION","target":"TARGET"}

target завжди рядок.

Дозволені action:
open_app, close_app, play_music, play_video, open_video_result,
find_content, open_url, web_search, find_file, open_file, find_folder,
open_path, delete_file, analyze_memory, set_volume, volume_up, volume_down,
mute, unmute, shutdown, restart, stop, chat, unknown

ПРОГРАМИ:
"відкрий Steam" -> open_app / "steam"
"закрий Chrome" -> close_app / "chrome"

МУЗИКА:
"включи музику" -> play_music / ""
"включи Imagine Dragons" -> play_music / "Imagine Dragons"

YOUTUBE:
play_video ТІЛЬКИ коли користувач явно каже YouTube/ютуб, "на YouTube", "відео"
або просить саме відео.
"відкрий Рік і Морті на YouTube" -> play_video / "Рік і Морті"
"знайди відео про космос" -> play_video / "космос"

ФІЛЬМИ, СЕРІАЛИ, ШОУ, АНІМЕ:
Якщо користувач хоче знайти, подивитися, запустити або включити названий контент,
але НЕ сказав YouTube, використовуй find_content.

ФАЙЛИ:
"знайди файл test.txt" -> find_file / "test.txt"
"відкрий файл test.txt" -> open_file / "test.txt"
"знайди папку Downloads" -> find_folder / "Downloads"
"видали файл test.txt" -> delete_file / "test.txt"

Файлові дії локально бажані, якщо команда однозначна. Не вигадуй повні шляхи.

FOLLOW-UP:
Контекст є частиною поточного діалогу.
Якщо користувач каже "його", "її", "там", "перше", "друге", "відкрий це",
визначай посилання на попередній результат.
Не вигадуй нову назву, якщо її можна взяти з context.

WEB SEARCH:
Актуальна інформація, новини, погода, курс, ціни -> web_search.

SYSTEM:
Явне вимкнення ПК -> shutdown.
Явне перезавантаження -> restart.
"стоп", "вихід", "досить" -> stop.

CHAT:
Звичайне спілкування -> chat.
Для chat target є короткою природною відповіддю українською.
Без markdown та емодзі.

ВАЖЛИВО:
Не виконуй дію самостійно. Тільки класифікуй команду.
Не вважай стару команду новою дією.
"target" має містити тільки потрібну назву або параметр.
"""


def _parse_command(command: str, context=None):
    if not client:
        print("[brain] OpenAI client недоступний.")
        return {"action": "unknown", "target": ""}

    context = context or []

    payload = {
        "command": command.strip(),
        "context": context,
    }

    try:
        response = client.responses.create(
            model=AZURE_OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            input=json.dumps(payload, ensure_ascii=False),
        )

        raw = response.output_text.strip()
        print(f"[brain] GPT raw: {raw}")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            cleaned = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)

        action = data.get("action", "unknown")
        target = str(data.get("target", "") or "").strip()

        if action not in ALLOWED_ACTIONS:
            action = "unknown"

        return {"action": action, "target": target}

    except Exception as e:
        print(f"[brain] GPT parser error: {e}")
        return {"action": "unknown", "target": ""}


def handle(command: str, context=None):
    global _last_action, _last_target

    if not command or not command.strip():
        _last_action = None
        _last_target = None
        return {"action": "unknown", "target": ""}

    print("[brain] Передаю команду GPT...")
    parsed = _parse_command(command.strip(), context=context or [])

    _last_action = parsed["action"]
    _last_target = parsed["target"]

    print(f"[brain] Intent: {_last_action}")
    print(f"[brain] Target: {_last_target}")
    return parsed
