"""Windows UI automation and grounded visual interaction for JARVIS."""

from __future__ import annotations

import base64
import io
import json
import os
import time

from dotenv import load_dotenv

try:
    import uiautomation as auto
except ImportError:
    auto = None


def _require():
    if auto is None:
        raise RuntimeError("uiautomation не встановлений. Виконай: pip install uiautomation")


def _control_name(control) -> str:
    try:
        return (control.Name or "").strip()
    except Exception:
        return ""


def _control_type(control) -> str:
    try:
        return str(control.ControlTypeName or "")
    except Exception:
        return ""


def _is_useful(control) -> bool:
    return bool(_control_name(control) or _control_type(control))


def inspect_ui(max_depth: int = 6, max_items: int = 140) -> str:
    _require()
    root = auto.GetForegroundControl()
    if root is None:
        return "Не вдалося отримати foreground-вікно."
    lines = []
    seen = 0

    def walk(control, depth: int):
        nonlocal seen
        if seen >= max_items or depth > max_depth:
            return
        if _is_useful(control):
            name = _control_name(control) or "без назви"
            ctype = _control_type(control) or "невідомий"
            lines.append(f"{'  ' * depth}- {ctype}: {name}")
            seen += 1
        if depth >= max_depth or seen >= max_items:
            return
        try:
            children = control.GetChildren()
        except Exception:
            return
        for child in children:
            if seen >= max_items:
                break
            walk(child, depth + 1)

    walk(root, 0)
    if not lines:
        return "UI Automation не знайшов доступних елементів."
    header_name = _control_name(root) or "Foreground window"
    return f"Foreground: {header_name}\n" + "\n".join(lines)


def find_element(name: str):
    _require()
    query = str(name or "").strip()
    if not query:
        return None
    root = auto.GetForegroundControl()
    if root is None:
        return None
    try:
        exact = root.Control(searchDepth=15, Name=query)
        if exact.Exists(0.7):
            return exact
    except Exception:
        pass

    query_lower = query.lower()
    queue = [root]
    visited = 0
    while queue and visited < 10000:
        control = queue.pop(0)
        visited += 1
        name_value = _control_name(control)
        if name_value and query_lower == name_value.lower():
            return control
        try:
            queue.extend(control.GetChildren())
        except Exception:
            continue
    return None


def _is_text_target(name: str) -> bool:
    q = name.strip().lower()
    return q.startswith(".") or any(q.endswith(ext) for ext in (".py", ".txt", ".md", ".json", ".ini", ".yaml", ".yml"))


def _foreground_process_name() -> str:
    try:
        import ctypes
        import psutil
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return psutil.Process(pid.value).name().lower()
    except Exception:
        return ""


def _is_pycharm() -> bool:
    process_name = _foreground_process_name()
    if process_name in {"pycharm64.exe", "pycharm.exe"}:
        return True
    if auto is None:
        return False
    try:
        root = auto.GetForegroundControl()
        title = _control_name(root).lower() if root else ""
        return "pycharm" in title or "jetbrains" in title or "jarvis -" in title
    except Exception:
        return False


def _pycharm_open_file(name: str) -> str | None:
    """Open an exact project file in PyCharm without pixel clicking or keyboard leakage."""
    if not _is_pycharm() or not _is_text_target(name):
        return None
    try:
        import pyautogui
        import pyperclip
        print(f"[ui] PyCharm direct navigation: {name}")
        pyautogui.hotkey("ctrl", "shift", "n")
        time.sleep(0.7)
        previous_clipboard = None
        try:
            previous_clipboard = pyperclip.paste()
        except Exception:
            pass
        pyperclip.copy(name)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.35)
        pyautogui.press("enter")
        time.sleep(0.8)
        if previous_clipboard is not None:
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                pass
        return f"PYCHARM_OPENED:{name}"
    except Exception as exc:
        print(f"[ui] PyCharm navigation failed: {exc}")
        return None


def _ocr_click(name: str) -> str | None:
    try:
        from tools import ocr
        return ocr.click_text(name)
    except Exception as exc:
        print(f"[ocr] unavailable: {exc}")
        return None


def _before_after_click(x: int, y: int) -> bool:
    try:
        import pyautogui
        before = pyautogui.screenshot().convert("RGB")
        pyautogui.moveTo(x, y, duration=0.05)
        pyautogui.click()
        time.sleep(0.35)
        after = pyautogui.screenshot().convert("RGB")
        left, top = max(0, x - 40), max(0, y - 40)
        right, bottom = min(before.width, x + 41), min(before.height, y + 41)
        changed = total = 0
        for yy in range(top, bottom, 8):
            for xx in range(left, right, 8):
                total += 1
                a, b = before.getpixel((xx, yy)), after.getpixel((xx, yy))
                if sum(abs(a[i] - b[i]) for i in range(3)) > 45:
                    changed += 1
        score = changed / max(total, 1)
        print(f"[ui] Click verify: changed={score:.2%}")
        return score >= 0.01
    except Exception as exc:
        print(f"[ui] Click verify unavailable: {exc}")
        return True


def click_element(name: str) -> str:
    """UIA -> app-specific -> OCR -> OmniParser -> LLM Vision."""
    direct = _pycharm_open_file(name)
    if direct:
        return direct

    control = find_element(name)
    if control is None:
        print(f"[ui] UI Automation: не знайдено '{name}'.")
        if _is_text_target(name) or len(name.strip().split()) <= 3:
            ocr_result = _ocr_click(name)
            if ocr_result:
                return ocr_result
        grounded = _omniparser_click(name)
        if grounded:
            return grounded
        print(f"[ui] OmniParser недоступний/не знайшов '{name}'. Перемикаюсь на Vision.")
        return vision_click(name)

    try:
        control.SetFocus()
    except Exception:
        pass
    try:
        if not control.IsEnabled:
            ocr_result = _ocr_click(name)
            if ocr_result:
                return ocr_result
            grounded = _omniparser_click(name)
            return grounded or vision_click(name)
        control.Click()
        return f"UI_CLICKED:{_control_name(control)}"
    except Exception as exc:
        print(f"[ui] UI Automation click failed: {exc}. Перемикаюсь далі.")
        ocr_result = _ocr_click(name)
        if ocr_result:
            return ocr_result
        grounded = _omniparser_click(name)
        return grounded or vision_click(name)


def _capture_screen():
    import pyautogui
    image = pyautogui.screenshot().convert("RGB")
    return image, image.size


def _encode_png(image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _encode_image(image, quality: int = 58) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _target_hint(name: str) -> str:
    q = name.strip().lower()
    if _is_text_target(q):
        return "Це назва текстового файла. Шукай точний текст у дереві файлів, не вкладці й не коді."
    if any(word in q for word in ("шестер", "gear", "settings", "налаштуван")):
        return "Це іконка шестерні/налаштувань. Вибирай лише справжній значок шестерні."
    return "Знаходь саме названий елемент, не схожий об'єкт. При неоднозначності found=false."


def _vision_request(name: str, detail: str, image) -> tuple[dict, tuple[int, int]]:
    load_dotenv()
    key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    model = os.getenv("AZURE_OPENAI_MODEL", "gpt-5-mini")
    if not key or not endpoint:
        raise RuntimeError("VISION_UNAVAILABLE")
    from openai import OpenAI
    prompt = (
        f"Знайди на screenshot елемент '{name}'. {_target_hint(name)} "
        "Поверни ТІЛЬКИ JSON без markdown: "
        "{\"found\":true/false,\"x\":number,\"y\":number,\"confidence\":number}. "
        "x,y = центр елемента в пікселях поточного screenshot. Не роби припущень."
    )
    response = OpenAI(api_key=key, base_url=endpoint).responses.create(
        model=model,
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": f"data:image/jpeg;base64,{_encode_image(image)}", "detail": detail},
        ]}],
    )
    raw = response.output_text.strip()
    data = json.loads(raw.replace("```json", "").replace("```", "").strip())
    return data, image.size


def _omniparser_click(name: str) -> str | None:
    try:
        from tools import omniparser
        if not omniparser.is_available():
            return None
        image, size = _capture_screen()
        element = omniparser.ground(_encode_png(image), name)
        if not element:
            print(f"[omniparser] Точного елемента '{name}' не знайдено.")
            return None
        x, y = omniparser.center(element, size)
        print(f"[omniparser] '{name}' -> {x},{y} element={element.get('id')}")
        verified = _before_after_click(x, y)
        return f"OMNI_CLICKED:{name}:{x},{y}:verified={verified}"
    except Exception as exc:
        print(f"[omniparser] grounding error: {exc}")
        return None


def vision_click(name: str) -> str:
    """Last-resort LLM vision click."""
    if not name:
        return "VISION_NO_TARGET"
    try:
        import pyautogui
        started = time.perf_counter()
        image, image_size = _capture_screen()
        if _is_text_target(name):
            data, image_size = _vision_request(name, "high", image)
        else:
            data, image_size = _vision_request(name, "low", image)
            confidence = float(data.get("confidence", 0) or 0)
            if (not data.get("found")) or confidence < 0.80:
                data, image_size = _vision_request(name, "high", image)
        if not data.get("found"):
            return f"Елемент '{name}' не знайдено через Vision."
        confidence = float(data.get("confidence", 0) or 0)
        if confidence < 0.75:
            return f"Vision знайшов '{name}', але впевненість недостатня ({confidence:.2f})."
        x, y = int(data.get("x", -1)), int(data.get("y", -1))
        if not (0 <= x < image_size[0] and 0 <= y < image_size[1]):
            return "Vision повернув некоректні координати."
        print(f"[ui] Vision: '{name}' -> {x},{y} confidence={confidence:.2f} latency={time.perf_counter() - started:.2f}s")
        verified = _before_after_click(x, y)
        return f"VISION_CLICKED:{name}:{x},{y}:verified={verified}"
    except Exception as exc:
        print(f"[ui] Vision fallback error: {exc}")
        return f"VISION_ERROR:{exc}"


def get_foreground_name() -> str:
    _require()
    root = auto.GetForegroundControl()
    if root is None:
        return "Foreground-вікно не знайдено."
    return f"Активне вікно: {_control_name(root) or 'без назви'}."
