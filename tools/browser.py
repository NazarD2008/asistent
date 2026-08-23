
"""
JARVIS Browser / YouTube

Можливості:
- відкриття URL;
- пошук YouTube через YouTube Data API;
- збереження останніх результатів;
- відкриття конкретного результату;
- YouTube Music;
- пошук фільмів;
- короткі відповіді для голосового режиму.
"""

import os
import re
import urllib.parse
import webbrowser

from dotenv import load_dotenv


# ============================================================
# ENV
# ============================================================

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


# ============================================================
# ОСТАННІ РЕЗУЛЬТАТИ YOUTUBE
# ============================================================

_last_results = []


# ============================================================
# OPEN URL
# ============================================================

def open_url(url: str) -> str:

    if not url:
        return "Не вказано адресу."

    url = str(url).strip()

    if not url:
        return "Не вказано адресу."

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:

        webbrowser.open_new_tab(url)

        print(
            f"[browser] Відкрито URL: {url}"
        )

        return f"Відкрито: {url}"

    except Exception as e:

        print(
            f"[browser] Помилка відкриття URL: {e}"
        )

        return "Не вдалося відкрити адресу."


# ============================================================
# YOUTUBE API SEARCH
# ============================================================

def _youtube_search(
    query: str,
    max_results: int = 5,
):

    global _last_results

    if not YOUTUBE_API_KEY:

        print(
            "[browser] YOUTUBE_API_KEY не знайдено."
        )

        _last_results = []

        return []

    try:

        import requests

    except ImportError:

        print(
            "[browser] Не встановлено requests."
        )

        _last_results = []

        return []

    url = (
        "https://www.googleapis.com/"
        "youtube/v3/search"
    )

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10,
        )

    except Exception as e:

        print(
            f"[browser] Помилка HTTP YouTube: {e}"
        )

        _last_results = []

        return []

    if response.status_code != 200:

        print(
            f"[browser] YouTube API "
            f"{response.status_code}: "
            f"{response.text}"
        )

        _last_results = []

        return []

    try:

        data = response.json()

    except Exception as e:

        print(
            f"[browser] Помилка JSON YouTube: {e}"
        )

        _last_results = []

        return []

    results = []

    for item in data.get("items", []):

        video_id = (
            item
            .get("id", {})
            .get("videoId")
        )

        snippet = item.get(
            "snippet",
            {}
        )

        title = snippet.get(
            "title",
            "Без назви"
        )

        channel = snippet.get(
            "channelTitle",
            "Невідомий канал"
        )

        if not video_id:
            continue

        results.append(
            {
                "id": video_id,
                "title": title,
                "channel": channel,
            }
        )

    _last_results = results

    print(
        f"[browser] YouTube знайдено: "
        f"{len(results)} відео"
    )

    for index, video in enumerate(
        results,
        start=1
    ):

        print(
            f"[browser] {index}. "
            f"{video['title']}"
        )

        print(
            f"           Канал: "
            f"{video['channel']}"
        )

        print(
            f"           ID: "
            f"{video['id']}"
        )

    return results


# ============================================================
# PLAY VIDEO / SEARCH
# ============================================================

def play_video(query: str = "") -> str:

    global _last_results

    query = str(
        query or ""
    ).strip()

    if not query:

        _last_results = []

        try:

            webbrowser.open_new_tab(
                "https://www.youtube.com"
            )

        except Exception as e:

            print(
                f"[browser] "
                f"Помилка YouTube: {e}"
            )

            return "Не вдалося відкрити YouTube."

        return "Відкриваю YouTube."

    results = _youtube_search(
        query=query,
        max_results=5
    )

    # ========================================================
    # API SUCCESS
    # ========================================================

    if results:

        search_url = (
            "https://www.youtube.com/results"
            "?search_query="
            + urllib.parse.quote(query)
        )

        try:

            webbrowser.open_new_tab(
                search_url
            )

            print(
                "[browser] "
                "Відкрито сторінку результатів YouTube."
            )

        except Exception as e:

            print(
                f"[browser] "
                f"Помилка відкриття YouTube: {e}"
            )

            return (
                f"Знайшов {len(results)} відео, "
                f"але не зміг відкрити браузер."
            )

        print(
            "[browser] Активний список YouTube збережено."
        )

        return (
            f"Знайшов {len(results)} відео. "
            f"Яке відкрити?"
        )

    # ========================================================
    # API FAILED
    # ========================================================

    _last_results = []

    search_url = (
        "https://www.youtube.com/results"
        "?search_query="
        + urllib.parse.quote(query)
    )

    try:

        webbrowser.open_new_tab(
            search_url
        )

        print(
            "[browser] YouTube API недоступний."
        )

    except Exception as e:

        print(
            f"[browser] "
            f"Помилка відкриття YouTube: {e}"
        )

        return (
            f"Не вдалося виконати "
            f"пошук «{query}»."
        )

    return (
        f"Шукаю на YouTube: {query}."
    )


# ============================================================
# OPEN VIDEO NUMBER
# ============================================================

def open_video_number(number) -> str:

    global _last_results

    try:

        number = int(number)

    except (
        ValueError,
        TypeError
    ):

        return "Не зрозумів номер відео."

    if not _last_results:

        return (
            "Немає збережених результатів. "
            "Спочатку скажи, що знайти."
        )

    if number < 1:

        return (
            "Номер відео має бути не менше 1."
        )

    if number > len(_last_results):

        return (
            f"У списку немає відео номер {number}. "
            f"Доступно від 1 до {len(_last_results)}."
        )

    video = _last_results[
        number - 1
    ]

    video_id = video.get(
        "id"
    )

    title = video.get(
        "title",
        "Без назви"
    )

    channel = video.get(
        "channel",
        "Невідомий канал"
    )

    if not video_id:

        return (
            "У цього результату "
            "немає YouTube ID."
        )

    url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    print(
        f"[browser] Відкриваю відео №{number}"
    )

    print(
        f"[browser] Назва: {title}"
    )

    print(
        f"[browser] Канал: {channel}"
    )

    print(
        f"[browser] URL: {url}"
    )

    try:

        webbrowser.open_new_tab(
            url
        )

    except Exception as e:

        print(
            f"[browser] "
            f"Помилка відкриття відео: {e}"
        )

        return (
            f"Знайшов відео «{title}», "
            f"але не зміг його відкрити."
        )

    _last_results = []

    print(
        "[browser] Результати YouTube очищено."
    )

    return (
        f"Відкриваю відео номер {number}."
    )


# ============================================================
# COMPATIBILITY
# ============================================================

def open_video_result(number) -> str:

    return open_video_number(number)


# ============================================================
# GET RESULTS
# ============================================================

def get_last_results():

    return list(
        _last_results
    )


# ============================================================
# HAS RESULTS
# ============================================================

def has_last_results() -> bool:

    return bool(
        _last_results
    )


# ============================================================
# CLEAR RESULTS
# ============================================================

def clear_last_results():

    global _last_results

    _last_results = []

    print(
        "[browser] Результати YouTube очищено."
    )


# ============================================================
# MUSIC
# ============================================================

def play_music(query: str = "") -> str:

    query = str(
        query or ""
    ).strip()

    if query:

        url = (
            "https://music.youtube.com/search?q="
            + urllib.parse.quote(query)
        )

        try:

            webbrowser.open_new_tab(
                url
            )

        except Exception as e:

            print(
                f"[browser] "
                f"Помилка YouTube Music: {e}"
            )

            return (
                "Не вдалося відкрити "
                "YouTube Music."
            )

        return (
            f"Шукаю музику: {query}."
        )

    try:

        webbrowser.open_new_tab(
            "https://music.youtube.com"
        )

    except Exception as e:

        print(
            f"[browser] "
            f"Помилка YouTube Music: {e}"
        )

        return (
            "Не вдалося відкрити "
            "YouTube Music."
        )

    return "Відкриваю YouTube Music."


# ============================================================
# FIND MOVIE
# ============================================================

def find_movie(query: str = "") -> str:
    """
    Шукає фільм через Google.
    
    Не намагається сам визначати сайт.
    Просто відкриває пошук за запитом.
    """

    query = str(
        query or ""
    ).strip()

    if not query:

        return "Не вказано назву фільму."

    search_query = (
        f"{query} фільм"
    )

    url = (
        "https://www.google.com/search?q="
        + urllib.parse.quote(search_query)
    )

    try:

        webbrowser.open_new_tab(
            url
        )

        print(
            f"[browser] Пошук фільму: "
            f"{query}"
        )

        return (
            f"Шукаю фільм {query}."
        )

    except Exception as e:

        print(
            f"[browser] "
            f"Помилка пошуку фільму: {e}"
        )

        return (
            "Не вдалося відкрити "
            "пошук фільму."
        )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "=" * 60
    )

    print(
        "JARVIS BROWSER TEST"
    )

    print(
        "=" * 60
    )

    while True:

        command = input(
            "\nКоманда: "
        ).strip()

        if not command:
            continue

        if command.lower() in (
            "exit",
            "quit",
            "стоп"
        ):

            break

        if command.lower().startswith(
            "фільм "
        ):

            print(
                find_movie(
                    command[6:]
                )
            )

        else:

            print(
                play_video(command)
            )

