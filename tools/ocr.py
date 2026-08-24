"""Optional local OCR grounding for JARVIS.

Uses Tesseract when installed. OCR is a fast text-target fallback before
OmniParser/LLM Vision.
"""

from __future__ import annotations

import shutil
from typing import Optional


def _tesseract_available() -> bool:
    return bool(shutil.which("tesseract"))


def find_text(target: str):
    target = str(target or "").strip()
    if not target or not _tesseract_available():
        return None

    try:
        import pyautogui
        import pytesseract
        from pytesseract import Output

        image = pyautogui.screenshot()
        data = pytesseract.image_to_data(image, output_type=Output.DICT, config="--psm 11")
        wanted = target.casefold()
        best = None

        for i, raw in enumerate(data.get("text", [])):
            text = str(raw or "").strip()
            if not text:
                continue
            score = 1.0 if text.casefold() == wanted else 0.0
            if score == 0.0 and wanted in text.casefold():
                score = 0.9
            if score == 0.0:
                continue

            try:
                x = int(data["left"][i])
                y = int(data["top"][i])
                w = int(data["width"][i])
                h = int(data["height"][i])
                conf = float(data.get("conf", [0])[i])
            except Exception:
                continue

            candidate = {
                "text": text,
                "x": x + w // 2,
                "y": y + h // 2,
                "confidence": max(score, min(1.0, conf / 100.0)),
            }
            if best is None or candidate["confidence"] > best["confidence"]:
                best = candidate

        if best and best["confidence"] >= 0.75:
            print(f"[ocr] '{target}' -> {best['x']},{best['y']} confidence={best['confidence']:.2f}")
            return best
    except Exception as exc:
        print(f"[ocr] error: {exc}")

    return None


def click_text(target: str) -> Optional[str]:
    result = find_text(target)
    if not result:
        return None
    try:
        import pyautogui
        pyautogui.moveTo(result["x"], result["y"], duration=0.05)
        pyautogui.click()
        return f"OCR_CLICKED:{target}:{result['x']},{result['y']}"
    except Exception as exc:
        print(f"[ocr] click error: {exc}")
        return None
