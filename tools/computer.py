"""JARVIS computer control tools for Windows."""

import os
import tempfile
from datetime import datetime

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

_SCREENSHOT_DIR = os.path.join(tempfile.gettempdir(), "jarvis")


def _require_pyautogui():
    if pyautogui is None:
        raise RuntimeError("pyautogui не встановлений. Виконай: pip install pyautogui")


def screenshot(path: str | None = None) -> str:
    _require_pyautogui()
    if path:
        output = os.path.abspath(os.path.expanduser(path))
    else:
        os.makedirs(_SCREENSHOT_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = os.path.join(_SCREENSHOT_DIR, f"screen_{stamp}.png")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    pyautogui.screenshot().save(output)
    return output


def mouse_move(x: int, y: int, duration: float = 0.2) -> str:
    _require_pyautogui()
    pyautogui.moveTo(int(x), int(y), duration=float(duration))
    return f"Курсор переміщено на {int(x)}, {int(y)}."


def click(x: int | None = None, y: int | None = None, button: str = "left") -> str:
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(int(x), int(y), button=button)
    else:
        pyautogui.click(button=button)
    return "Клік виконано."


def double_click(x: int | None = None, y: int | None = None) -> str:
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.doubleClick(int(x), int(y))
    else:
        pyautogui.doubleClick()
    return "Подвійний клік виконано."


def type_text(text: str, interval: float = 0.01) -> str:
    _require_pyautogui()
    value = str(text)
    if pyperclip is None:
        return "Не вдалося ввести текст: pyperclip не встановлений."
    pyperclip.copy(value)
    pyautogui.hotkey("ctrl", "v")
    return "Текст вставлено в активне поле."


def press(key: str) -> str:
    _require_pyautogui()
    pyautogui.press(str(key))
    return f"Клавішу {key} натиснуто."


def hotkey(*keys: str) -> str:
    _require_pyautogui()
    if not keys:
        return "Не вказані клавіші."
    pyautogui.hotkey(*(str(key) for key in keys))
    return f"Комбінацію {' + '.join(str(key) for key in keys)} виконано."


def get_mouse_position() -> str:
    _require_pyautogui()
    x, y = pyautogui.position()
    return f"Курсор зараз на {x}, {y}."
