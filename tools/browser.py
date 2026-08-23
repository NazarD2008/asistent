"""JARVIS Browser / YouTube / content search."""

import os
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
            results.append({
                "id": video_id,
                "title": snippet.get("title", "Без назви"),
                "channel": snippet.get("channelTitle", "Невідомий канал"),
            })
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


def _justwatch_locale():
    """Повертає локаль JustWatch для України."""
    try:
        import requests
        response = requests.get(
            "https://apis.justwatch.com/content/locales/state",
            headers={"User-Agent": "JARVIS/1.0"},
            timeout=8,
        )
        response.raise_for_status()
        for item in response.json():
            if item.get("iso_3166_2") == "UA" or item.get("country") == "UA":
                return item.get("full_locale")
    except Exception as e:
        print(f"[browser] JustWatch locale error: {e}")

    # Якщо список локалей недоступний, для українського каталогу
    # використовуємо стандартну локаль JustWatch.
    return "uk_UA"


def _justwatch_search(query: str):
    """Шукає тайтл через JustWatch та повертає його country-specific URL."""
    try:
        import requests

        locale = _justwatch_locale()
        url = f"https://apis.justwatch.com/content/titles/{locale}/popular"

        payload = {
            "age_certifications": None,
            "content_types": ["movie", "show"],
            "presentation_types": None,
            "providers": None,
            "genres": None,
            "languages": None,
            "release_year_from": None,
            "release_year_until": None,
            "monetization_types": None,
            "min_price": None,
            "max_price": None,
            "nationwide_cinema_releases_only": None,
            "scoring_filter_types": None,
            "cinema_release": None,
            "query": query,
            "page": 1,
            "page_size": 10,
            "timeline_type": None,
            "person_id": None,
        }

        response = requests.post(
            url,
            json=payload,
            headers={
                "User-Agent": "JARVIS/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("items") or []

        if not items:
            return None

        query_norm = " ".join(query.lower().split())
        exact = [
            item for item in items
            if " ".join(str(item.get("title", "")).lower().split()) == query_norm
            or " ".join(str(item.get("original_title", "")).lower().split()) == query_norm
        ]
        item = exact[0] if exact else items[0]

        path = item.get("full_path")
        if not path:
            return None

        return {
            "title": item.get("title") or item.get("original_title") or query,
            "url": "https://www.justwatch.com" + path,
        }

    except Exception as e:
        print(f"[browser] JustWatch search error: {e}")
        return None


def find_content(query: str = "") -> str:
    """Знаходить найкращий тайтл і відкриває його сторінку JustWatch."""
    query = str(query or "").strip()
    if not query:
        return "Не вказано назву контенту."

    print(f"[browser] Пошук контенту: {query}")

    result = _justwatch_search(query)
    if result:
        try:
            webbrowser.open_new_tab(result["url"])
            print(f"[browser] JustWatch результат: {result['url']}")
            return f"Знайшов {result['title']}. Відкриваю сторінку, де його можна подивитися."
        except Exception as e:
            print(f"[browser] Помилка відкриття JustWatch: {e}")

    google_query = f'"{query}" дивитися онлайн Україна'
    google_url = "https://www.google.com/search?q=" + urllib.parse.quote(google_query)
    try:
        webbrowser.open_new_tab(google_url)
        print(f"[browser] Fallback Google: {google_url}")
        return f"Не знайшов готову сторінку. Відкриваю пошук для {query}."
    except Exception:
        return "Не вдалося виконати пошук контенту."


def find_movie(query: str = "") -> str:
    return find_content(query)
