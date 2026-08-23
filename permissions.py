"""
permissions.py
Контроль підтвердження для небезпечних дій JARVIS.

Будь-який інструмент, що може незворотно змінити систему
(видалення файлів, зміна реєстру, вимкнення ПК, форматування тощо),
повинен бути обгорнутий декоратором @requires_confirmation.
"""

from functools import wraps

# Патерни, які завжди вважаються небезпечними, навіть у сирих shell-командах
DANGEROUS_KEYWORDS = [
    "del ", "remove-item", "format", "rd /s", "rmdir /s",
    "shutdown", "reg delete", "diskpart",
]


class ActionCancelled(Exception):
    """Піднімається, коли користувач відхилив підтвердження."""
    pass


def is_dangerous_command(command: str) -> bool:
    """Груба перевірка тексту shell-команди на небезпечні патерни."""
    low = command.lower()
    return any(word in low for word in DANGEROUS_KEYWORDS)


# ============================================================
# CONFIRMATION BACKEND
# ============================================================
#
# За замовчуванням підтвердження йде через консоль (input()).
# У голосовому режимі Jarvis.py підміняє це на голосове
# підтвердження через set_confirm_handler(voice.voice_confirm).

def _console_confirm(question: str) -> bool:

    print(f"\n⚠️  ПІДТВЕРДЖЕННЯ ПОТРІБНЕ\n{question}")

    answer = input("Підтвердити? (так/ні): ").strip().lower()

    return answer in ("так", "т", "y", "yes")


_confirm_handler = _console_confirm


def set_confirm_handler(handler):
    """
    Підміняє спосіб підтвердження.
    handler(question: str) -> bool
    """

    global _confirm_handler

    _confirm_handler = handler


def requires_confirmation(description_fn=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            question = description_fn(*args, **kwargs) if description_fn \
                else f"Виконати дію '{func.__name__}' з аргументами {args}?"

            confirmed = _confirm_handler(question)

            if not confirmed:
                print("❌ Дію скасовано.")
                raise ActionCancelled(f"Дію скасовано: {func.__name__}")

            print("✅ Підтверджено, виконую…")
            return func(*args, **kwargs)

        return wrapper
    return decorator