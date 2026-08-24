"""Windows UI Automation tools for JARVIS.

Primary desktop perception layer before Vision fallback.
Uses Windows UI Automation through `uiautomation`; Vision is fallback.
"""

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
    """UI Automation first; Vision fallback only when UIA cannot find/click the element."""
    control = find_element(name)
    if control is None:
        print(f"[ui] UI Automation: не знайдено '{name}'. Перемикаюсь на Vision.")
        return vision_click(name)

    try:
        control.SetFocus()
    except Exception:
        pass

    try:
        if not control.IsEnabled:
            print(f"[ui] UI element disabled: {_control_name(control)}. Перемикаюсь на Vision.")
            return vision_click(name)
        control.Click()
        return f"UI_CLICKED:{_control_name(control)}"
    except Exception as e:
        print(f"[ui] UI Automation click failed: {e}. Перемикаюсь на Vision.")
        return vision_click(name)


def _screenshot_data(max_width: int = 1280):
    import pyautogui

    image = pyautogui.screenshot().convert("RGB")
    original_size = image.size
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)))
    shown_size = image.size
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=62, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("utf-8"), original_size, shown_size


def _call_vision(name: str, detail: str):
    load_dotenv()
    key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    model = os.getenv("AZURE_OPENAI_MODEL", "gpt-5-mini")
    if not key or not endpoint:
        return None

    from openai import OpenAI

    image_b64, original_size, shown_size = _screenshot_data()
    response = OpenAI(api_key=key, base_url=endpoint).responses.create(
        model=model,
        input=[{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        f"Find the UI element '{name}' on this Windows screenshot. "
                        "Return ONLY JSON: "
                        "{\"found\":true/false,\"x\":number,\"y\":number,\"confidence\":number}. "
                        "x,y are coordinates relative to the image you received. "
                        "Return the CENTER of the element. If absent, found=false."
                    ),
                },
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{image_b64}",
                    "detail": detail,
                },
            ],
        }],
    )
    raw = response.output_text.strip()
    data = json.loads(raw.replace("```json", "").replace("```", "").strip())
    return data, original_size, shown_size


def vision_click(name: str) -> str:
    """Fast low-detail Vision first; high-detail retry only when needed."""
    if not name:
        return "VISION_NO_TARGET"

    try:
        import pyautogui

        started = time.perf_counter()
        used_detail = "low"
        result = _call_vision(name, "low")
        if result is None:
            return "VISION_UNAVAILABLE"
        data, original_size, shown_size = result
        confidence = float(data.get("confidence", 0) or 0)

        # If low-detail is uncertain, retry once with high detail.
        if not data.get("found") or confidence < 0.60:
            used_detail = "high"
            result = _call_vision(name, "high")
            if result is None:
                return "VISION_UNAVAILABLE"
            data, original_size, shown_size = result
            confidence = float(data.get("confidence", 0) or 0)

        if not data.get("found"):
            return f"Елемент '{name}' не знайдено через Vision."
        if confidence < 0.60:
            return f"Vision знайшов '{name}', але впевненість занадто низька ({confidence:.2f})."

        x = int(data.get("x", -1))
        y = int(data.get("y", -1))
        if not (0 <= x < shown_size[0] and 0 <= y < shown_size[1]):
            return "Vision повернув некоректні координати."

        # Map coordinates from the resized image back to the real screen.
        sx = original_size[0] / shown_size[0]
        sy = original_size[1] / shown_size[1]
        screen_x = int(round(x * sx))
        screen_y = int(round(y * sy))

        latency = time.perf_counter() - started
        print(
            f"[ui] Vision: '{name}' -> image={x},{y} screen={screen_x},{screen_y} "
            f"confidence={confidence:.2f} detail={used_detail} latency={latency:.2f}s"
        )

        pyautogui.click(screen_x, screen_y)
        time.sleep(0.25)
        return f"VISION_CLICKED:{name}:{screen_x},{screen_y}"

    except Exception as e:
        print(f"[ui] Vision fallback error: {e}")
        return f"VISION_ERROR:{e}"


def get_foreground_name() -> str:
    _require()
    root = auto.GetForegroundControl()
    if root is None:
        return "Foreground-вікно не знайдено."
    return f"Активне вікно: {_control_name(root) or 'без назви'}."
