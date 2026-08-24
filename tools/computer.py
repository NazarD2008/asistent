"""JARVIS computer control tools for Windows."""

import os
import tempfile
import time
from datetime import datetime

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import win32con
    import win32gui
    import win32process
    import win32api
except ImportError:
    win32con = None
    win32gui = None
    win32process = None
    win32api = None

_SCREENSHOT_DIR = os.path.join(tempfile.gettempdir(), "jarvis")

PROCESS_ALIASES = {"chrome": ("chrome.exe",), "firefox": ("firefox.exe",), "edge": ("msedge.exe",), "discord": ("Discord.exe",), "steam": ("steam.exe",), "telegram": ("Telegram.exe",), "vs code": ("Code.exe",), "code": ("Code.exe",), "explorer": ("explorer.exe",), "notepad": ("notepad.exe",)}


def _require_pyautogui():
    if pyautogui is None:
        raise RuntimeError("pyautogui не встановлений. Виконай: pip install pyautogui")


def screenshot(path=None):
    _require_pyautogui()
    if path:
        output = os.path.abspath(os.path.expanduser(path))
    else:
        os.makedirs(_SCREENSHOT_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        output = os.path.join(_SCREENSHOT_DIR, f"screen_{stamp}.png")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    pyautogui.screenshot().save(output)
    return output


def mouse_move(x, y, duration=0.2):
    _require_pyautogui()
    pyautogui.moveTo(int(x), int(y), duration=float(duration))
    return f"Курсор переміщено на {int(x)}, {int(y)}."


def click(x=None, y=None, button="left"):
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(int(x), int(y), button=button)
    else:
        pyautogui.click(button=button)
    return "Клік виконано."


def double_click(x=None, y=None):
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.doubleClick(int(x), int(y))
    else:
        pyautogui.doubleClick()
    return "Подвійний клік виконано."


def _foreground():
    if win32gui is None:
        return None
    try:
        return win32gui.GetForegroundWindow()
    except Exception:
        return None


def _native_paste():
    if win32api is not None and win32con is not None:
        try:
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord("V"), 0, 0, 0)
            win32api.keybd_event(ord("V"), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.25)
            return True
        except Exception:
            pass
    _require_pyautogui()
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.25)
    return True


def type_text(text, interval=0.01):
    if pyperclip is None:
        return "Не вдалося ввести текст: pyperclip не встановлений."
    value = str(text)
    if not value:
        return "Порожній текст."
    try:
        pyperclip.copy(value)
        time.sleep(0.25)
        hwnd = _foreground()
        if hwnd and win32gui is not None:
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.15)
            except Exception:
                pass
        _native_paste()
        return "Текст введено."
    except Exception as e:
        print(f"[computer] Paste error: {e}")
        return "Не вдалося ввести текст."


def press(key):
    _require_pyautogui()
    pyautogui.press(str(key))
    return f"Клавішу {key} натиснуто."


def hotkey(*keys):
    _require_pyautogui()
    if not keys:
        return "Не вказані клавіші."
    pyautogui.hotkey(*(str(key) for key in keys))
    return f"Комбінацію {' + '.join(str(key) for key in keys)} виконано."


def get_mouse_position():
    _require_pyautogui()
    x, y = pyautogui.position()
    return f"Курсор зараз на {x}, {y}."


def focus_process(app_name):
    if psutil is None or win32gui is None or win32process is None:
        return False
    names = {n.lower() for n in PROCESS_ALIASES.get(str(app_name).strip().lower(), ())}
    if not names:
        return False
    candidates = []
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if (proc.info.get("name") or "").lower() in names:
                    candidates.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        return False
    if not candidates:
        return False
    target_hwnd = None
    def enum_handler(hwnd, _):
        nonlocal target_hwnd
        if target_hwnd is not None or not win32gui.IsWindowVisible(hwnd):
            return
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid in candidates and win32gui.GetWindowText(hwnd).strip():
                target_hwnd = hwnd
        except Exception:
            pass
    try:
        win32gui.EnumWindows(enum_handler, None)
        if target_hwnd is None:
            return False
        if win32gui.IsIconic(target_hwnd):
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(target_hwnd)
        time.sleep(0.35)
        return True
    except Exception:
        return False
