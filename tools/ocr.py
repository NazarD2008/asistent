"""Local OCR grounding for JARVIS.

OCR searches visible application windows while excluding JARVIS' own process
and its parent console/IDE windows. This lets commands typed into the JARVIS
console target text visible in another application such as Notepad or Chrome.
"""

from __future__ import annotations

import ctypes
import os
import re
import shutil
import time
from typing import Optional

TESSERACT_PATHS = (
    os.getenv("TESSERACT_CMD", ""),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def _tesseract_cmd() -> str | None:
    for path in TESSERACT_PATHS:
        if path and os.path.isfile(path):
            return path
    return shutil.which("tesseract")


def _normalize(text: str) -> str:
    text = str(text or "").casefold().replace("ё", "е")
    text = re.sub(r"[^\w\sА-Яа-яІіЇїЄєҐґ'\.-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _ancestor_pids() -> set[int]:
    result: set[int] = set()
    try:
        import psutil
        process = psutil.Process(os.getpid())
        while process:
            result.add(process.pid)
            parent = process.parent()
            if parent is None or parent.pid in result:
                break
            process = parent
    except Exception:
        result.add(os.getpid())
    return result


def _window_info(hwnd: int):
    if not ctypes.windll.user32.IsWindowVisible(hwnd) or ctypes.windll.user32.IsIconic(hwnd):
        return None

    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    rect = RECT()
    if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
    if right - left < 120 or bottom - top < 60:
        return None

    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    title_buffer = ctypes.create_unicode_buffer(max(length + 1, 2))
    ctypes.windll.user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
    title = title_buffer.value.strip()

    pid = ctypes.c_ulong()
    ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    pid_value = int(pid.value)
    try:
        import psutil
        process_name = psutil.Process(pid_value).name().lower()
    except Exception:
        process_name = ""

    return {"hwnd": hwnd, "pid": pid_value, "title": title, "process": process_name, "rect": (left, top, right, bottom)}


def _visible_app_windows():
    windows = []
    blocked = _ancestor_pids()
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @enum_proc
    def callback(hwnd, _lparam):
        info = _window_info(int(hwnd))
        if not info or info["pid"] in blocked:
            return True
        title = info["title"].casefold()
        if any(marker in title for marker in ("jarvis –", "jarvis -", "jarvis")):
            return True
        windows.append(info)
        return True

    ctypes.windll.user32.EnumWindows(callback, 0)
    return windows[:12]


def _rows_from_ocr(image):
    import pytesseract
    from pytesseract import Output
    cmd = _tesseract_cmd()
    if not cmd:
        print("[ocr] Tesseract не знайдений.")
        return None
    pytesseract.pytesseract.tesseract_cmd = cmd
    return pytesseract.image_to_data(image, lang="ukr+eng", output_type=Output.DICT, config="--oem 3 --psm 11")


def _find_in_window(target: str, window):
    import pyautogui
    left, top, right, bottom = window["rect"]
    screen = pyautogui.screenshot()
    screen_w, screen_h = screen.size
    crop_left, crop_top = max(0, left), max(0, top)
    crop_right, crop_bottom = min(screen_w, right), min(screen_h, bottom)
    if crop_right <= crop_left or crop_bottom <= crop_top:
        return None
    image = screen.crop((crop_left, crop_top, crop_right, crop_bottom))
    data = _rows_from_ocr(image)
    if not data:
        return None

    wanted = _normalize(target)
    rows = []
    for i, raw in enumerate(data.get("text", [])):
        raw = str(raw or "").strip()
        if not raw:
            continue
        try:
            x, y = int(data["left"][i]), int(data["top"][i])
            w, h = int(data["width"][i]), int(data["height"][i])
            conf = float(data.get("conf", [0])[i])
            line_num = int(data.get("line_num", [0])[i])
            block_num = int(data.get("block_num", [0])[i])
        except Exception:
            continue
        rows.append({"text": raw, "norm": _normalize(raw), "x": x, "y": y, "w": w, "h": h, "confidence": max(0.0, min(1.0, conf / 100.0)), "line": (block_num, line_num)})

    best = None
    for item in rows:
        if item["norm"] == wanted:
            best = {"text": item["text"], "x": item["x"] + item["w"] // 2 + crop_left, "y": item["y"] + item["h"] // 2 + crop_top, "confidence": max(0.75, item["confidence"])}
            break

    if best is None and " " in wanted:
        grouped = {}
        for item in rows:
            grouped.setdefault(item["line"], []).append(item)
        for group in grouped.values():
            group.sort(key=lambda x: (x["y"], x["x"]))
            for start in range(len(group)):
                combined = []
                min_x = min_y = max_x = max_y = None
                confs = []
                for end in range(start, min(len(group), start + 8)):
                    item = group[end]
                    combined.append(item["norm"])
                    text = " ".join(combined).strip()
                    if not text:
                        continue
                    if min_x is None:
                        min_x, min_y = item["x"], item["y"]
                        max_x, max_y = item["x"] + item["w"], item["y"] + item["h"]
                    else:
                        min_x = min(min_x, item["x"]); min_y = min(min_y, item["y"])
                        max_x = max(max_x, item["x"] + item["w"]); max_y = max(max_y, item["y"] + item["h"])
                    confs.append(item["confidence"])
                    if text == wanted:
                        best = {"text": " ".join(x["text"] for x in group[start:end + 1]), "x": (min_x + max_x) // 2 + crop_left, "y": (min_y + max_y) // 2 + crop_top, "confidence": max(0.75, min(confs) if confs else 0.0)}
                        break
                    if len(text) > len(wanted):
                        break
                if best is not None:
                    break
            if best is not None:
                break

    if best:
        best["window_title"] = window["title"]
        best["window_process"] = window["process"]
        best["window_rect"] = window["rect"]
    return best


def find_text(target: str):
    target = str(target or "").strip()
    if not target or not _tesseract_cmd():
        return None
    started = time.perf_counter()
    try:
        windows = _visible_app_windows()
        if not windows:
            print("[ocr] Не знайдено видимих вікон для OCR.")
            return None
        print(f"[ocr] Шукаю '{target}' у {len(windows)} видимих вікнах...")
        for window in windows:
            result = _find_in_window(target, window)
            if result and result["confidence"] >= 0.75:
                print(f"[ocr] '{target}' -> {result['x']},{result['y']} confidence={result['confidence']:.2f} window={result['window_title']!r} rect={result['window_rect']} process={result['window_process']} latency={time.perf_counter() - started:.2f}s")
                return result
        print(f"[ocr] Текст '{target}' не знайдено у видимих вікнах.")
    except Exception as exc:
        print(f"[ocr] error: {exc}")
    return None


def click_text(target: str) -> Optional[str]:
    result = find_text(target)
    if not result:
        return None
    try:
        import pyautogui
        before = pyautogui.screenshot().convert("RGB")
        x, y = result["x"], result["y"]
        pyautogui.moveTo(x, y, duration=0.05)
        pyautogui.click()
        time.sleep(0.35)
        after = pyautogui.screenshot().convert("RGB")
        changed = total = 0
        for yy in range(max(0, y - 32), min(before.height, y + 33), 8):
            for xx in range(max(0, x - 32), min(before.width, x + 33), 8):
                total += 1
                a, b = before.getpixel((xx, yy)), after.getpixel((xx, yy))
                if sum(abs(a[i] - b[i]) for i in range(3)) > 45:
                    changed += 1
        verified = changed / max(total, 1) >= 0.01
        print(f"[ocr] Click verify: changed={changed}/{max(total,1)} verified={verified} window={result['window_title']!r}")
        return f"OCR_CLICKED:{target}:{x},{y}:verified={verified}"
    except Exception as exc:
        print(f"[ocr] click error: {exc}")
        return None
