"""Local OCR grounding for JARVIS.

OCR is limited to the visible foreground window so text in JARVIS' own
console cannot be mistaken for text inside another minimized application.
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


def _foreground_rect():
    """Return the visible foreground window rectangle, or None if minimized."""
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if not hwnd:
        return None
    if ctypes.windll.user32.IsIconic(hwnd):
        return None

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    rect = RECT()
    if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return None
    return rect.left, rect.top, rect.right, rect.bottom


def _rows_from_ocr(image):
    import pytesseract
    from pytesseract import Output

    cmd = _tesseract_cmd()
    if not cmd:
        print("[ocr] Tesseract не знайдений.")
        return None
    pytesseract.pytesseract.tesseract_cmd = cmd

    return pytesseract.image_to_data(
        image,
        lang="ukr+eng",
        output_type=Output.DICT,
        config="--oem 3 --psm 11",
    )


def find_text(target: str):
    target = str(target or "").strip()
    if not target:
        return None

    cmd = _tesseract_cmd()
    if not cmd:
        print("[ocr] Tesseract не знайдений.")
        return None

    try:
        import pyautogui

        rect = _foreground_rect()
        if not rect:
            print("[ocr] Немає видимого foreground-вікна. OCR пропущено.")
            return None

        left, top, right, bottom = rect
        screenshot = pyautogui.screenshot()
        image = screenshot.crop((left, top, right, bottom))
        data = _rows_from_ocr(image)
        if not data:
            return None

        wanted = _normalize(target)
        rows = []
        count = len(data.get("text", []))

        for i in range(count):
            raw = str(data.get("text", [""])[i] or "").strip()
            if not raw:
                continue
            try:
                x = int(data["left"][i])
                y = int(data["top"][i])
                w = int(data["width"][i])
                h = int(data["height"][i])
                conf = float(data.get("conf", [0])[i])
                line_num = int(data.get("line_num", [0])[i])
                block_num = int(data.get("block_num", [0])[i])
            except Exception:
                continue

            rows.append({
                "text": raw,
                "norm": _normalize(raw),
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "confidence": max(0.0, min(1.0, conf / 100.0)),
                "line": (block_num, line_num),
            })

        best = None

        for item in rows:
            if item["norm"] == wanted:
                candidate = {
                    "text": item["text"],
                    "x": item["x"] + item["w"] // 2 + left,
                    "y": item["y"] + item["h"] // 2 + top,
                    "confidence": max(0.75, item["confidence"]),
                }
                if best is None or candidate["confidence"] > best["confidence"]:
                    best = candidate

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
                            min_x = min(min_x, item["x"])
                            min_y = min(min_y, item["y"])
                            max_x = max(max_x, item["x"] + item["w"])
                            max_y = max(max_y, item["y"] + item["h"])
                        confs.append(item["confidence"])

                        if text == wanted:
                            candidate = {
                                "text": " ".join(x["text"] for x in group[start:end + 1]),
                                "x": (min_x + max_x) // 2 + left,
                                "y": (min_y + max_y) // 2 + top,
                                "confidence": max(0.75, min(confs) if confs else 0.0),
                            }
                            if best is None or candidate["confidence"] > best["confidence"]:
                                best = candidate
                            break
                        if len(text) > len(wanted):
                            break

        if best:
            print(
                f"[ocr] '{target}' -> {best['x']},{best['y']} "
                f"confidence={best['confidence']:.2f} "
                f"window={left},{top},{right},{bottom} "
                f"cmd={cmd} lang=ukr+eng"
            )
            return best

        print(f"[ocr] Текст '{target}' не знайдено у foreground-вікні.")

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
        print(f"[ocr] Click verify: changed={changed}/{max(total,1)} verified={verified}")
        return f"OCR_CLICKED:{target}:{x},{y}:verified={verified}"

    except Exception as exc:
        print(f"[ocr] click error: {exc}")
        return None
