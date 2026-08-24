"""Optional Playwright browser agent for DOM-level automation.

Keeps browser interaction separate from screen vision. Uses installed Chrome
with a persistent JARVIS profile, so cookies/sign-ins can persist.
"""

from __future__ import annotations

import atexit
import os
import urllib.parse

_playwright = None
_context = None
_page = None


def _profile_dir() -> str:
    base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~/.jarvis")
    path = os.path.join(base, "Jarvis", "browser-profile")
    os.makedirs(path, exist_ok=True)
    return path


def _ensure_page():
    global _playwright, _context, _page
    if _page is not None and not _page.is_closed():
        return _page

    from playwright.sync_api import sync_playwright

    if _playwright is None:
        _playwright = sync_playwright().start()

    if _context is None:
        try:
            _context = _playwright.chromium.launch_persistent_context(
                user_data_dir=_profile_dir(),
                channel="chrome",
                headless=False,
                viewport=None,
                args=["--start-maximized"],
            )
        except Exception as exc:
            raise RuntimeError(
                "Не вдалося запустити Chrome через Playwright. Перевір, що Google Chrome встановлений."
            ) from exc

    _page = _context.pages[0] if _context.pages else _context.new_page()
    _page.set_default_timeout(5000)
    return _page


def _close():
    global _context, _playwright
    try:
        if _context is not None:
            _context.close()
    except Exception:
        pass
    try:
        if _playwright is not None:
            _playwright.stop()
    except Exception:
        pass


atexit.register(_close)


def open_page(url: str) -> str:
    page = _ensure_page()
    page.goto(url, wait_until="domcontentloaded", timeout=20000)
    return f"Відкрито сторінку: {page.title()}"


def search(query: str, site: str = "google") -> str:
    query = str(query or "").strip()
    if not query:
        return "Не вказано пошуковий запит."

    if site.lower() in {"youtube", "ютуб"}:
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        page = _ensure_page()
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.locator("a#video-title").first.wait_for(timeout=7000)
        titles = page.locator("a#video-title").all_inner_texts()[:5]
        clean = [title.strip() for title in titles if title.strip()]
        if clean:
            return "YouTube: " + " | ".join(clean)
        return f"Відкрив пошук YouTube для: {query}."

    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    page = _ensure_page()
    page.goto(url, wait_until="domcontentloaded", timeout=20000)
    return f"Відкрив пошук Google для: {query}."


def click_text(text: str) -> str:
    page = _ensure_page()
    target = str(text or "").strip()
    if not target:
        return "Не вказано текст елемента."

    candidates = [
        page.get_by_role("button", name=target, exact=True),
        page.get_by_role("link", name=target, exact=True),
        page.get_by_text(target, exact=True),
        page.get_by_text(target, exact=False),
    ]
    for locator in candidates:
        try:
            if locator.count() > 0:
                locator.first.click()
                return f"Натиснув: {target}."
        except Exception:
            continue
    return f"Не знайшов елемент у браузері: {target}."


def type_text(text: str) -> str:
    page = _ensure_page()
    page.keyboard.type(str(text or ""))
    return "Текст введено в браузер."


def press(key: str) -> str:
    page = _ensure_page()
    page.keyboard.press(str(key or "Enter"))
    return f"Натиснуто {key}."


def current_page() -> str:
    page = _ensure_page()
    return f"{page.title()} | {page.url}"
