"""
JARVIS Brain

Відповідає за розуміння складних команд через GPT.
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
        client = OpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            base_url=AZURE_OPENAI_ENDPOINT,
        )
        print("[brain] OpenAI client готовий.")
    except Exception as e:
        print(f"[brain] Помилка створення OpenAI client: {e}")

ALLOWED_ACTIONS = {
    "open_app", "close_app", "play_music", "play_video",
    "open_video_result", "find_content", "open_url", "web_search",
    "delete_file", "analyze_memory", "set_volume", "volume_up",
    "volume_down", "mute", "unmute", "shutdown", "restart",
    "stop", "chat", "unknown",
}

_last_action = None
_last_target = None


def get_last_parsed():
    return _last_action, _last_target


def _parse_command(command: str, context=None):
    if not client:
        print("[brain] OpenAI client недоступний.")
        return {"action": "unknown", "target": ""}

    context = context or []

    system_prompt = """
Ти мозок голосового асистента JARVIS.
Визначай НАМІР користувача, а не окремі ключові слова.
ПОВЕРТАЙ ТІЛЬКИ JSON:
{"action":"ACTION","target":"TARGET"}

Дозволені action:
open_app, close_app, play_music, play_video, open_video_result,
find_content, open_url, web_search, delete_file, analyze_memory,
set_volume, volume_up, volume_down, mute, unmute, shutdown, restart,
stop, chat, unknown

target завжди рядок. Не вигадуй параметри.

ПРОГРАМИ:
"відкрий Steam" -> open_app, target="steam"
"закрий Chrome" -> close_app, target="chrome"

МУЗИКА:
"включи музику" -> play_music, target=""
"включи Imagine Dragons" -> play_music, target="Imagine Dragons"

YOUTUBE:
play_video використовуй ТІЛЬКИ якщо користувач ЯВНО каже "відео", "на YouTube",
"ютуб", "YouTube" або явно просить знайти відео.
"відкрий Рік і Морті на YouTube" -> play_video, target="Рік і Морті"
"знайди відео про космос" -> play_video, target="космос"

ФІЛЬМИ / СЕРІАЛИ / ШОУ / АНІМЕ / ІНШИЙ КОНТЕНТ:
Використовуй find_content, якщо користувач хоче знайти, подивитися, запустити,
увімкнути або дізнатися де подивитися названий фільм, серіал, шоу, аніме тощо,
АЛЕ не вказав YouTube.
Це універсальне правило для будь-якої назви, не тільки конкретних тайтлів.

Приклади:
"включи Рік і Морті" -> find_content, target="Рік і Морті"
"хочу подивитися Інтерстеллар" -> find_content, target="Інтерстеллар"
"де подивитися Breaking Bad" -> find_content, target="Breaking Bad"
"запусти Гаррі Поттера" -> find_content, target="Гаррі Поттер"

ВАЖЛИВО: не залишай службові слова в target. Target має бути назвою контенту.
Наприклад "знайде фільм інтерстел" -> target="Інтерстел".

YOUTUBE FOLLOW-UP:
Якщо context показує останній список YouTube результатів,
"перше", "друге", "відкрий 2" -> open_video_result з номером.

WEB SEARCH:
Актуальна інформація, погода, новини, курс, ціни -> web_search.

SYSTEM:
Явне вимкнення ПК -> shutdown.
Явне перезавантаження -> restart.
"стоп", "вихід", "досить" -> stop.

CHAT:
Звичайне спілкування -> chat.
Для chat target є готовою короткою природною відповіддю українською,
без markdown та емодзі.

CONTEXT:
Використовуй context для follow-up команд і займенників.
Не вважай попередню команду поточною дією.
"""

    try:
        response = client.responses.create(
            model=AZURE_OPENAI_MODEL,
            instructions=system_prompt,
            input=json.dumps({"command": command, "context": context}, ensure_ascii=False),
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
