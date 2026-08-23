"""JARVIS computer control tools for Windows."""

import ctypes
import os
import tempfile
import time
from ctypes import wintypes
from datetime import datetime

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import win32con
    import win32gui
    import win32process
except ImportError:
    win32con = None
    win32gui = None
    win32process = None

_SCREENSHOT_DIR = os.path.join(tempfile.gettempdir(), "jarvis")

PROCESS_ALIASES = {
    "chrome": ("chrome.exe",),
    "firefox": ("firefox.exe",),
    "edge": ("msedge.exe",),
    "discord": ("Discord.exe",),
    "steam": ("steam.exe",),
    "telegram": ("Telegram.exe",),
    "vs code": ("Code.exe",),
    "code": ("Code.exe",),
    "explorer": ("explorer.exe",),
    "notepad": ("notepad.exe",),
}


def _require_pyautogui():
    if pyautogui is None:
        raise RuntimeError("pyautogui не встановлений. Виконай: pip install pyautogui")


def screenshot(path: str | None = None) -> str:
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


# ============================================================
# WINDOWS UNICODE INPUT
# ============================================================

if os.name == "nt":
    ULONG_PTR = wintypes.WPARAM

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [
            ("type", wintypes.DWORD),
            ("u", INPUT_UNION),
        ]

    _user32 = ctypes.windll.user32
    _user32.SendInput.argtypes = (
        wintypes.UINT,
        ctypes.POINTER(INPUT),
        ctypes.c_int,
    )
    _user32.SendInput.restype = wintypes.UINT

    _INPUT_KEYBOARD = 1
    _KEYEVENTF_KEYUP = 0x0002
    _KEYEVENTF_UNICODE = 0x0004


def _send_unicode_text(text: str):
    """Надсилає Unicode-символи напряму Windows без clipboard."""
    if os.name != "nt":
        raise RuntimeError("Unicode SendInput доступний тільки у Windows.")

    inputs = []
    for char in str(text):
        codepoint = ord(char)

        # BMP-символи
        if codepoint <= 0xFFFF:
            inputs.append(
                INPUT(
                    type=_INPUT_KEYBOARD,
                    u=INPUT_UNION(
                        ki=KEYBDINPUT(
                            wVk=0,
                            wScan=codepoint,
                            dwFlags=_KEYEVENTF_UNICODE,
                            time=0,
                            dwExtraInfo=0,
                        )
                    ),
                )
            )
            inputs.append(
                INPUT(
                    type=_INPUT_KEYBOARD,
                    u=INPUT_UNION(
                        ki=KEYBDINPUT(
                            wVk=0,
                            wScan=codepoint,
                            dwFlags=_KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP,
                            time=0,
                            dwExtraInfo=0,
                        )
                    ),
                )
            )
        else:
            # Windows Unicode input для символів поза BMP через UTF-16 surrogate pair.
            codepoint -= 0x10000
            high = 0xD800 + ((codepoint >> 10) & 0x3FF)
            low = 0xDC00 + (codepoint & 0x3FF)
            for unit in (high, low):
                inputs.append(
                    INPUT(
                        type=_INPUT_KEYBOARD,
                        u=INPUT_UNION(
                            ki=KEYBDINPUT(
                                wVk=0,
                                wScan=unit,
                                dwFlags=_KEYEVENTF_UNICODE,
                                time=0,
                                dwExtraInfo=0,
                            )
                        ),
                    )
                )
                inputs.append(
                    INPUT(
                        type=_INPUT_KEYBOARD,
                        u=INPUT_UNION(
                            ki=KEYBDINPUT(
                                wVk=0,
                                wScan=unit,
                                dwFlags=_KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP,
                                time=0,
                                dwExtraInfo=0,
                            )
                        ),
                    )
                )

    if inputs:
        array = (INPUT * len(inputs))(*inputs)
        sent = _user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            raise RuntimeError(f"Windows SendInput ввів лише {sent} з {len(inputs)} подій.")


def type_text(text: str, interval: float = 0.01) -> str:
    value = str(text)
    try:
        _send_unicode_text(value)
        return "Текст введено."
    except Exception as e:
        print(f"[computer] Unicode SendInput error: {e}")
        _require_pyautogui()
        pyautogui.write(value, interval=float(interval))
        return "Текст введено резервним способом."


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


def focus_process(app_name: str) -> bool:
    """Знаходить головне видиме вікно процесу та переводить його у foreground."""
    if psutil is None or win32gui is None or win32process is None:
        return False

    names = set(PROCESS_ALIASES.get(str(app_name).strip().lower(), ()))
    if not names:
        return False

    candidates = []
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name in {n.lower() for n in names}:
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
        if target_hwnd is not None:
            return
        if not win32gui.IsWindowVisible(hwnd):
            return
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            return
        if pid in candidates:
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                target_hwnd = hwnd

    try:
        win32gui.EnumWindows(enum_handler, None)
    except Exception:
        return False

    if target_hwnd is None:
        return False

    try:
        if win32gui.IsIconic(target_hwnd):
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(target_hwnd)
        time.sleep(0.15)
        return True
    except Exception:
        return False
