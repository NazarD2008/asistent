"""Optional local OmniParser client for visual grounding.

The client is deliberately optional. When a local OmniParser HTTP server is
available, JARVIS can use its structured UI elements instead of asking the
LLM to guess raw screen coordinates.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

DEFAULT_URL = "http://127.0.0.1:7860/process_image"


def endpoint() -> str:
    return os.getenv("OMNIPARSER_URL", DEFAULT_URL).rstrip("/")


def is_available(timeout: float = 0.4) -> bool:
    """Return True when the configured local parser endpoint responds."""
    try:
        url = endpoint().replace("/process_image", "")
        response = requests.get(url, timeout=timeout)
        return response.ok
    except Exception:
        return False


def _post_image(image_bytes: bytes, timeout: float = 8.0) -> dict[str, Any] | None:
    try:
        response = requests.post(
            endpoint(),
            files={"image": ("screen.png", image_bytes, "image/png")},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:
        print(f"[omniparser] unavailable: {exc}")
        return None


def _box_from_value(value: Any):
    if isinstance(value, dict):
        for key in ("bbox", "box", "bounding_box", "coordinates"):
            if key in value:
                return _box_from_value(value[key])
        if all(k in value for k in ("x1", "y1", "x2", "y2")):
            return [float(value["x1"]), float(value["y1"]), float(value["x2"]), float(value["y2"])]
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            return [float(v) for v in value]
        except (TypeError, ValueError):
            return None
    return None


def _extract_elements(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize common OmniParser API response shapes into element records."""
    candidates = (
        data.get("elements"),
        data.get("parsed_elements"),
        data.get("parsed_content_list"),
        data.get("parsed_content"),
        data.get("items"),
    )
    raw = next((item for item in candidates if isinstance(item, list)), None)
    if raw is None:
        return []

    global_boxes = data.get("bboxes") or data.get("bounding_boxes") or data.get("boxes")
    if isinstance(global_boxes, list):
        boxes = global_boxes
    else:
        boxes = []

    elements: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("content") or item.get("label") or item.get("description") or "").strip()
            box = _box_from_value(item)
            if box is None and index < len(boxes):
                box = _box_from_value(boxes[index])
        else:
            text = str(item).strip()
            box = _box_from_value(boxes[index]) if index < len(boxes) else None

        # Some OmniParser forks serialize bbox inside a text record.
        if box is None and text:
            match = re.search(r"(?:bbox|box)\s*[:=]\s*\[?\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)", text, re.I)
            if match:
                box = [float(match.group(i)) for i in range(1, 5)]

        if box is not None:
            elements.append({"id": index, "text": text, "bbox": box})

    return elements


def ground(image_bytes: bytes, target: str) -> dict[str, Any] | None:
    """Return the best matching structured UI element for target, or None."""
    data = _post_image(image_bytes)
    if not data:
        return None

    elements = _extract_elements(data)
    if not elements:
        return None

    query = target.strip().lower()
    if not query:
        return None

    def score(element: dict[str, Any]):
        text = str(element.get("text", "")).lower()
        if not text:
            return 0
        if text == query:
            return 100
        if query in text:
            return 80
        words = set(query.split())
        hits = sum(1 for word in words if word and word in text)
        return hits * 10

    ranked = sorted(elements, key=score, reverse=True)
    best = ranked[0] if ranked and score(ranked[0]) > 0 else None
    if best is None:
        return None

    box = best["bbox"]
    # Accept either absolute pixel boxes or normalized 0..1 boxes.
    if max(box) <= 1.0:
        best = dict(best)
        best["normalized"] = True
    else:
        best = dict(best)
        best["normalized"] = False
    return best


def center(element: dict[str, Any], image_size: tuple[int, int]) -> tuple[int, int]:
    x1, y1, x2, y2 = element["bbox"]
    if element.get("normalized"):
        width, height = image_size
        x1, x2 = x1 * width, x2 * width
        y1, y2 = y1 * height, y2 * height
    return int(round((x1 + x2) / 2)), int(round((y1 + y2) / 2))
