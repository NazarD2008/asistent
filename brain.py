"""JARVIS Brain - intent parsing, vision and planning."""

import base64
import io
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
    "open_app", "close_app", "play_music", "play_video", "open_video_result", "find_content", "open_url", "web_search",
    "find_file", "open_file", "find_folder", "open_path", "delete_file", "screenshot", "analyze_screen", "inspect_ui", "ui_click",
    "foreground_window", "mouse_move", "click", "double_click", "type_text", "press_key", "hotkey", "mouse_position", "analyze_memory",
    "set_volume", "volume_up", "volume_down", "mute", "unmute", "shutdown", "restart", "multi_action", "browser_search", "browser_open",
    "browser_click_text", "browser_type", "browser_press", "browser_current", "stop", "chat", "unknown",
}

_last_action = None
_last_target = None

def get_last_parsed():
    return _last_action, _last_target

SYSTEM_PROMPT = """
Ти мозок JARVIS. ПОВЕРТАЙ ТІЛЬКИ JSON.

Для однієї дії: {"action":"ACTION","target":"TARGET"}
Для кількох: {"action":"multi_action","target":"","steps":[{"action":"ACTION","target":"TARGET"},...]}

Дозволені action:
open_app, close_app, play_music, play_video, open_video_result, find_content, open_url, web_search,
find_file, open_file, find_folder, open_path, delete_file, screenshot, analyze_screen, inspect_ui, ui_click,
foreground_window, mouse_move, click, double_click, type_text, press_key, hotkey, mouse_position, analyze_memory,
set_volume, volume_up, volume_down, mute, unmute, shutdown, restart,
browser_search, browser_open, browser_click_text, browser_type, browser_press, browser_current,
multi_action, stop, chat, unknown

ПРОГРАМИ:
"відкрий Steam" -> open_app / "steam"
"закрий Chrome" -> close_app / "chrome"

YOUTUBE:
"знайди на YouTube відео про Minecraft" -> browser_search / "youtube|Minecraft"
"пошукай на ютубі урок Python" -> browser_search / "youtube|урок Python"
Якщо користувач просить саме відео/YouTube, перевага browser_search. Не використовуй screenshot для звичайного пошуку.

ФІЛЬМИ/СЕРІАЛИ:
Без YouTube -> find_content.

БРАУЗЕР:
browser_open = відкрити конкретний URL у керованому Chrome.
browser_search = DOM-пошук через Playwright. Перевага над Vision.
browser_click_text = натиснути текстовий/ARIA елемент у браузері.
browser_type = ввести текст у поточний браузер.
browser_press = натиснути клавішу в браузері.
"відкрий сторінку https://example.com" -> browser_open / URL

ФАЙЛИ:
"знайди файл test.txt" -> find_file / "test.txt"
"відкрий файл test.txt" -> open_file / "test.txt"
"знайди папку Downloads" -> find_folder / "Downloads"
"видали файл test.txt" -> delete_file / "test.txt"

ЕКРАН:
"зроби скріншот" -> screenshot / ""
"що зараз на екрані" -> analyze_screen / запит
Vision-відповідь максимум 3 коротких речення, без списків і повних шляхів.

WINDOWS UI:
UI Automation є першим способом. Для тексту/файлів перевага UIA/OCR/app-specific. Vision лише fallback.
"покажи елементи інтерфейсу" -> inspect_ui / ""
"яке активне вікно" -> foreground_window / ""
"натисни кнопку Settings" -> ui_click / "Settings"
"нажми на шестерню" -> ui_click / "шестерню"

КОМП'ЮТЕР:
"покажи координати миші" -> mouse_position / ""
"перемісти мишку на 500 300" -> mouse_move / "500 300"
"клікни на 500 300" -> click / "500 300"
"напиши Привіт" -> type_text / "Привіт"
"натисни Enter" -> press_key / "enter"
"натисни Ctrl+L" -> hotkey / "ctrl+l"

MULTI-ACTION:
Кілька послідовних дій -> multi_action.
Для браузера перевага browser_* tools над Vision.
Не вигадуй дій, крім очевидних технічних кроків, необхідних для виконання запиту.

FOLLOW-UP:
Контекст діалогу доступний. "його", "це", "перше", "друге" посилаються на попередні результати.

WEB SEARCH:
Актуальна інформація, новини, погода, курс, ціни -> web_search.

SYSTEM:
Вимкнення ПК -> shutdown. Перезавантаження -> restart. "стоп"/"вихід" -> stop.
CHAT:
Звичайне спілкування -> chat з короткою природною відповіддю українською.

Тільки класифікуй/плануй. Не виконуй дії самостійно.
"""


def _parse_command(command: str, context=None):
    if not client:
        print("[brain] OpenAI client недоступний.")
        return {"action": "unknown", "target": ""}
    payload = {"command": command.strip(), "context": context or []}
    try:
        response = client.responses.create(model=AZURE_OPENAI_MODEL, instructions=SYSTEM_PROMPT, input=json.dumps(payload, ensure_ascii=False))
        raw = response.output_text.strip()
        print(f"[brain] GPT raw: {raw}")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = json.loads(raw.replace("```json", "").replace("```", "").strip())
        action = data.get("action", "unknown")
        target = str(data.get("target", "") or "").strip()
        if action not in ALLOWED_ACTIONS:
            action = "unknown"
        parsed = {"action": action, "target": target}
        if action == "multi_action":
            steps = data.get("steps", [])
            if not isinstance(steps, list) or not steps:
                return {"action": "unknown", "target": ""}
            clean_steps = []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_action = step.get("action", "unknown")
                step_target = str(step.get("target", "") or "").strip()
                if step_action not in ALLOWED_ACTIONS or step_action == "multi_action":
                    continue
                clean_steps.append({"action": step_action, "target": step_target})
            if not clean_steps:
                return {"action": "unknown", "target": ""}
            parsed["steps"] = clean_steps
        return parsed
    except Exception as e:
        print(f"[brain] GPT parser error: {e}")
        return {"action": "unknown", "target": ""}


def analyze_screen(image_path: str, question: str, context=None) -> str:
    if not client:
        return "OpenAI client недоступний."
    try:
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        max_width = 1600
        if image.width > max_width:
            ratio = max_width / image.width
            image = image.resize((max_width, int(image.height * ratio)))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=68, optimize=True)
        base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
        response = client.responses.create(
            model=AZURE_OPENAI_MODEL,
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": "Ти бачиш екран Windows JARVIS. Відповідай українською максимум у 3 коротких реченнях. Без списків, без повних шляхів і зайвих технічних деталей. Кажи тільки те, що реально видно.\n\nЗапит: " + question},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}", "detail": "low"},
            ]}],
        )
        answer = response.output_text.strip()
        print(f"[brain] Vision: {answer}")
        return answer or "Не вдалося зрозуміти, що на екрані."
    except FileNotFoundError:
        return "Скріншот не знайдено."
    except Exception as e:
        print(f"[brain] Vision error: {e}")
        return "Не вдалося проаналізувати екран."


def handle(command: str, context=None):
    global _last_action, _last_target
    if not command or not command.strip():
        _last_action = None
        _last_target = None
        return {"action": "unknown", "target": ""}
    print("[brain] Передаю команду GPT...")
    parsed = _parse_command(command.strip(), context=context or [])
    _last_action = parsed["action"]
    _last_target = parsed.get("target", "")
    print(f"[brain] Intent: {_last_action}")
    print(f"[brain] Target: {_last_target}")
    return parsed
