"""
tools/shell.py
Виконання PowerShell-команд. Команди, що містять небезпечні патерни
(видалення, форматування, зміни реєстру, вимкнення), автоматично
проходять через підтвердження з permissions.py.
"""

import subprocess
from permissions import requires_confirmation, is_dangerous_command


def _run(command: str) -> str:

    try:

        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout.strip() or result.stderr.strip()

        return output or "Команду виконано (без виводу)."

    except subprocess.TimeoutExpired:

        return "Команда виконувалась занадто довго і була перервана (тайм-аут 30 секунд)."

    except FileNotFoundError:

        return "Не вдалося запустити PowerShell. Перевір, чи він встановлений."

    except Exception as e:

        print(
            f"[shell] Помилка виконання команди: {e}"
        )

        return "Не вдалося виконати команду."

@requires_confirmation(description_fn=lambda cmd: f"Виконати PowerShell-команду:\n  {cmd}")
def _run_confirmed(command: str) -> str:
    return _run(command)


def run_command(command: str) -> str:
    """Єдина точка входу: сама вирішує, чи потрібне підтвердження."""
    if is_dangerous_command(command):
        return _run_confirmed(command)
    return _run(command)
