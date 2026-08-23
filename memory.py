"""
memory.py
Короткочасна пам'ять JARVIS.

Зберігає останні команди та результати
протягом поточного запуску Jarvis.
"""

from collections import deque


MAX_MEMORY = 10

_history = deque(maxlen=MAX_MEMORY)


def add_user_message(text: str):
    """Зберегти повідомлення користувача."""

    if not text:
        return

    _history.append({
        "role": "user",
        "content": text.strip(),
    })


def add_assistant_message(text: str):
    """Зберегти відповідь JARVIS."""

    if not text:
        return

    _history.append({
        "role": "assistant",
        "content": text.strip(),
    })


def get_history():
    """Повернути історію."""

    return list(_history)


def clear_memory():
    """Очистити пам'ять."""

    _history.clear()


def get_context(limit: int = 10) -> str:
    """
    Перетворює історію у текст,
    який можна передати GPT.
    """

    history = list(_history)[-limit:]

    if not history:
        return "Історія порожня."

    lines = []

    for item in history:

        role = item["role"]
        content = item["content"]

        if role == "user":
            lines.append(
                f"Користувач: {content}"
            )

        else:
            lines.append(
                f"JARVIS: {content}"
            )

    return "\n".join(lines)