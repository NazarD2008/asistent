"""JARVIS Browser / YouTube / content search."""

import os
import re
import urllib.parse
import webbrowser

from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
_last_results = []


def open_url(url: str) -> str:
    if not url:
        return "Не вказано адресу."
    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        webbrowser.open_new_tab(url)
        print(f"[browser] Відкрито URL: {url}")
        return f"Відкрито: {url}"
    except Exception as e:
        print(f"[browser] Помилка відкриття URL: {e}")
        return "Не вдалося відкрити адресу."


def _youtube_search(query: str, max_results: int = 5):
    global _last_results
    if not YOUTUBE_API_KEY:
        _last_results = []
        return []
    try:
        import requests
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video", "maxResults": max_results, "key": YOUTUBE_API_KEY},
            timeout=10,
        )
        if response.status_code != 200:
            _last_results = []
            return []
        data = response.json()
    except Exception as e:
        print(f"[browser] Помилка YouTube: {e}")
        _last_results = []
        return []

    results = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        if video_id:
            results.append({"id": video_id, "title": snippet.get("title", "Без назви"), "channel": snippet.get("channelTitle", "Невідомий канал")})
    _last_results = results
    print(f"[browser] YouTube знайдено: {len(results)} відео")
    return results


def play_video(query: str = "") -> str:
    global _last_results
    query = str(query or "").strip()
    if not query:
        _last_results = []
        return open_url("https://www.youtube.com")
    results = _youtube_search(query)
    search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    try:
        webbrowser.open_new_tab(search_url)
    except Exception:
        return "Не вдалося відкрити YouTube."
    if results:
        return f"Знайшов {len(results)} відео. Яке відкрити?"
    return f"Шукаю на YouTube: {query}."


def open_video_number(number) -> str:
    global _last_results
    try:
        number = int(number)
    except (ValueError, TypeError):
        return "Не зрозумів номер відео."
    if not _last_results:
        return "Немає збережених результатів. Спочатку скажи, що знайти."
    if number < 1 or number > len(_last_results):
        return f"У списку немає відео номер {number}. Доступно від 1 до {len(_last_results)}."
    video = _last_results[number - 1]
    url = "https://www.youtube.com/watch?v=" + video["id"]
    webbrowser.open_new_tab(url)
    title = video.get("title", "Без назви")
    _last_results = []
    return f"Відкриваю відео «{title}»."


def open_video_result(number) -> str:
    return open_video_number(number)


def get_last_results():
    return list(_last_results)


def has_last_results() -> bool:
    return bool(_last_results)


def clear_last_results():
    global _last_results
    _last_results = []


def play_music(query: str = "") -> str:
    query = str(query or "").strip()
    url = "https://music.youtube.com"
    if query:
        url += "/search?q=" + urllib.parse.quote(query)
    try:
        webbrowser.open_new_tab(url)
        return f"Шукаю музику: {query}." if query else "Відкриваю YouTube Music."
    except Exception:
        return "Не вдалося відкрити YouTube Music."


def _google_first_result(query: str):
    """Повертає перший нормальний результат Google."""
    try:
        import requests
        from html import unescape

        url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"},
            timeout=10,
        )
        response.raise_for_status()
        html = response.text

        candidates = re.findall(r'href="(?:/url\?q=)?(https?://[^"&]+)', html)
        blocked = ("google.com", "googleusercontent.com", "gstatic.com", "youtube.com")
        for candidate in candidates:
            candidate = unescape(candidate)
            low = candidate.lower()
            if any(domain in low for domain in blocked):
                continue
            return candidate
    except Exception as e:
        print(f"[browser] Google first-result error: {e}")
    return None


def find_content(query: str = "") -> str:
    """Шукає фільм/серіал через Google і відкриває перший результат."""
    query = str(query or "").strip()
    if not query:
        return "Не вказано назву контенту."

    print(f"[browser] Пошук контенту: {query}")
    search_query = f"{query} дивитись онлайн"
    result_url = _google_first_result(search_query)

    if result_url:
        try:
            webbrowser.open_new_tab(result_url)
            print(f"[browser] Google first result: {result_url}")
            return f"Знайшов {query}. Відкриваю перший результат."
        except Exception as e:
            print(f"[browser] Помилка відкриття результату: {e}")

    google_url = "https://www.google.com/search?q=" + urllib.parse.quote(search_query)
    try:
        webbrowser.open_new_tab(google_url)
        print(f"[browser] Google fallback: {google_url}")
        return f"Відкриваю пошук для {query}."
    except Exception:
        return "Не вдалося виконати пошук контенту."


def find_movie(query: str = "") -> str:
    return find_content(query)
