"""Windows UI Automation tools for JARVIS.

Primary desktop perception layer before Vision fallback.
Uses Windows UI Automation through `uiautomation`; Vision is fallback.
"""

from __future__ import annotations

import base64
import io
import json
import os

from dotenv import load_dotenv

try:
    import uiautomation as auto
except ImportError:
    auto = None


def _require():
    if auto is None:
        raise RuntimeError(
            "uiautomation не встановлений. Виконай: pip install uiautomation"
        )


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


def inspect_ui(max_depth: int = 3, max_items: int = 80) -> str:
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
        exact = root.Control(searchDepth=10, Name=query)
        if exact.Exists(0.5):
            return exact
    except Exception:
        pass

    query_lower = query.lower()
    queue = [root]
    visited = 0
    while queue and visited < 5000:
        control = queue.pop(0)
        visited += 1
        name_value = _control_name(control)
        if name_value and query_lower in name_value.lower():
            return control
        try:
            queue.extend(control.GetChildren())
        except Exception:
            continue
    return None


def click_element(name: str) -> str:
    """UI Automation click. Never reports success unless an element was found and clicked."""
    control = find_element(name)
    if control is None:
        return f"UI_NOT_FOUND:{name}"

    try:
        control.SetFocus()
    except Exception:
        pass

    try:
        if not control.IsEnabled:
            return f"UI_DISABLED:{_control_name(control)}"
        control.Click()
        return f"UI_CLICKED:{_control_name(control)}"
    except Exception as e:
        return f"UI_CLICK_FAILED:{_control_name(control)}:{e}"


def _screenshot_data():
    import pyautogui
    image = pyautogui.screenshot().convert("RGB")
    original_size = image.size
    if image.width > 1600:
        ratio = 1600 / image.width
        image = image.resize((1600, int(image.height * ratio)))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=72, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("utf-8"), original_size


def vision_click(name: str) -> str:
    """Vision fallback when UI Automation cannot find the requested element."""
    load_dotenv()
    key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    model = os.getenv("AZURE_OPENAI_MODEL", "gpt-5-mini")
    if not key or not endpoint:
        return "VISION_UNAVAILABLE"

    try:
        from openai import OpenAI
        import pyautogui

        image_b64, original_size = _screenshot_data()
        response = OpenAI(api_key=key, base_url=endpoint).responses.create(
            model=model,
            input=[{
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            f"Знайди на екрані елемент '{name}'. "
                            "Поверни ТІЛЬКИ JSON: "
                            "{\"found\":true/false,\"x\":number,\"y\":number,\"confidence\":number}. "
                            "x,y повинні бути координатами центра елемента в оригінальному screenshot. "
                            "Якщо елемента немає, found=false."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{image_b64}",
                        "detail": "high",
                    },
                ],
            }],
        )
        raw = response.output_text.strip()
        data = json.loads(raw.replace("```json", "").replace("```", "").strip())
        if not data.get("found"):
            return f"Елемент '{name}' не знайдено навіть через Vision."
        confidence = float(data.get("confidence", 0))
        if confidence < 0.70:
            return f"Vision знайшов '{name}', але впевненість занадто низька ({confidence:.2f})."

        x = int(data["x"])
        y = int(data["y"])
        if not (0 <= x < original_size[0] and 0 <= y < original_size[1]):
            return "Vision повернув некоректні координати."

        pyautogui.click(x, y)
        return f"VISION_CLICKED:{name}:{x},{y}"
    except Exception as e:
        print(f"[ui] Vision fallback error: {e}")
        return f"VISION_ERROR:{e}"


def get_foreground_name() -> str:
    _require()
    root = auto.GetForegroundControl()
    if root is None:
        return "Foreground-вікно не знайдено."
    return f"Активне вікно: {_control_name(root) or 'без назви'}."
