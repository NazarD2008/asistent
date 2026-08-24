"""Local OCR grounding for JARVIS."""

from __future__ import annotations

import os
import re
from typing import Optional


TESSERACT_PATHS = (
    os.getenv("TESSERACT_CMD", ""),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def _tesseract_cmd() -> str | None:
    import shutil

    for path in TESSERACT_PATHS:
        if path and os.path.isfile(path):
            return path
    return shutil.which("tesseract")


def _normalize(text: str) -> str:
    text = str(text or "").casefold().replace("ё", "е")
    text = re.sub(r"[^\w\sА-Яа-яІіЇїЄєҐґ'\.-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tesseract_available() -> bool:
    return bool(_tesseract_cmd())


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
        import pytesseract
        from pytesseract import Output

        pytesseract.pytesseract.tesseract_cmd = cmd
        image = pyautogui.screenshot()
        data = pytesseract.image_to_data(
            image,
            lang="ukr+eng",
            output_type=Output.DICT,
            config="--psm 11",
        )

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

        # First try exact individual token match.
        for item in rows:
            if item["norm"] == wanted:
                candidate = {
                    "text": item["text"],
                    "x": item["x"] + item["w"] // 2,
                    "y": item["y"] + item["h"] // 2,
                    "confidence": max(0.75, item["confidence"]),
                }
                if best is None or candidate["confidence"] > best["confidence"]:
                    best = candidate

        # Multi-word target: combine neighboring OCR boxes on the same line.
        if best is None and " " in wanted:
            grouped = {}
            for item in rows:
                grouped.setdefault(item["line"], []).append(item)

            for group in grouped.values():
                group.sort(key=lambda x: (x["y"], x["x"]))
                for start in range(len(group)):
                    combined = []
                    min_x = min_y = None
                    max_x = max_y = None
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
                                "x": (min_x + max_x) // 2,
                                "y": (min_y + max_y) // 2,
                                "confidence": max(0.75, min(confs) if confs else 0.0),
                            }
                            if best is None or candidate["confidence"] > best["confidence"]:
                                best = candidate
                            break
                        if len(text) > len(wanted) and not text.startswith(wanted + " "):
                            break

        if best:
            print(
                f"[ocr] '{target}' -> {best['x']},{best['y']} "
                f"confidence={best['confidence']:.2f} cmd={cmd} lang=ukr+eng"
            )
            return best

        print(f"[ocr] Текст '{target}' не знайдено.")

    except Exception as exc:
        print(f"[ocr] error: {exc}")

    return None


def click_text(target: str) -> Optional[str]:
    result = find_text(target)
    if not result:
        return None

    try:
        import pyautogui
        import time

        before = pyautogui.screenshot().convert("RGB")
        pyautogui.moveTo(result["x"], result["y"], duration=0.05)
        pyautogui.click()
        time.sleep(0.35)
        after = pyautogui.screenshot().convert("RGB")

        x, y = result["x"], result["y"]
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
