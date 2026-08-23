"""
tools/system.py

Системні функції JARVIS:
- аналіз ПК
- RAM / CPU / диски
- керування гучністю Windows
- mute / unmute
- вимкнення
- перезавантаження
"""

import subprocess

import psutil

from permissions import requires_confirmation


# ============================================================
# PYCAW
# ============================================================

try:
    from pycaw.pycaw import AudioUtilities

    PYCAW_AVAILABLE = True

except ImportError:
    PYCAW_AVAILABLE = False


# ============================================================
# АНАЛІЗ ПК
# ============================================================

def analyze_memory() -> str:
    """
    Показує:
    - CPU
    - RAM
    - диск C
    - топ процесів за RAM
    """

    # -------------------------
    # RAM
    # -------------------------

    mem = psutil.virtual_memory()

    used_gb = mem.used / (1024 ** 3)
    total_gb = mem.total / (1024 ** 3)
    available_gb = mem.available / (1024 ** 3)

    # -------------------------
    # CPU
    # -------------------------

    cpu = psutil.cpu_percent(interval=0.7)

    # -------------------------
    # DISK C
    # -------------------------

    disk = psutil.disk_usage("C:\\")

    disk_used = disk.used / (1024 ** 3)
    disk_total = disk.total / (1024 ** 3)
    disk_free = disk.free / (1024 ** 3)

    # -------------------------
    # ПРОЦЕСИ
    # -------------------------

    processes = []

    for process in psutil.process_iter(
        ["name", "memory_info", "cpu_percent"]
    ):
        try:
            name = process.info["name"] or "Unknown"

            memory_info = process.info["memory_info"]

            if memory_info:
                ram_mb = memory_info.rss / (1024 ** 2)
            else:
                ram_mb = 0

            cpu_usage = process.info["cpu_percent"] or 0

            processes.append(
                (
                    ram_mb,
                    cpu_usage,
                    name,
                )
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    # Топ-3 процеси за RAM
    top3 = sorted(
        processes,
        key=lambda x: x[0],
        reverse=True,
    )[:3]

    if top3:

        top_str = ", ".join(
            f"{name} ({ram:.0f} МБ)"
            for ram, cpu_usage, name in top3
        )

    else:

        top_str = "дані недоступні"

    # -------------------------
    # ВІДПОВІДЬ
    # -------------------------

    return (
        f"Процесор завантажений на {cpu:.0f} відсотків. "
        f"Оперативна пам'ять: {mem.percent:.0f} відсотків, "
        f"{used_gb:.1f} з {total_gb:.1f} ГБ використовується, "
        f"доступно {available_gb:.1f} ГБ. "
        f"Диск C: зайнято {disk_used:.1f} з {disk_total:.1f} ГБ, "
        f"вільно {disk_free:.1f} ГБ. "
        f"Найбільше RAM використовують: {top_str}."
    )


# ============================================================
# AUDIO
# ============================================================

def _get_volume():
    """
    Отримує системний аудіовихід Windows.

    ВАЖЛИВО:

    У нових версіях pycaw:

        AudioUtilities.GetSpeakers()

    повертає AudioDevice.

    Тому НЕ можна робити:

        devices.Activate(...)

    Замість цього використовується:

        devices.EndpointVolume
    """

    if not PYCAW_AVAILABLE:

        raise RuntimeError(
            "pycaw не встановлений. "
            "Виконай: pip install pycaw comtypes"
        )

    devices = AudioUtilities.GetSpeakers()

    # --------------------------------------------------------
    # НОВИЙ PYCAW
    # --------------------------------------------------------

    if hasattr(devices, "EndpointVolume"):

        return devices.EndpointVolume

    # --------------------------------------------------------
    # РЕЗЕРВНИЙ ВАРІАНТ ДЛЯ СТАРИХ ВЕРСІЙ PYCAW
    # --------------------------------------------------------

    try:

        from pycaw.pycaw import IAudioEndpointVolume
        from comtypes import CLSCTX_ALL

        interface = devices.Activate(
            IAudioEndpointVolume._iid_,
            CLSCTX_ALL,
            None,
        )

        return interface.QueryInterface(
            IAudioEndpointVolume
        )

    except Exception as e:

        raise RuntimeError(
            f"Не вдалося отримати аудіопристрій: {e}"
        )


# ============================================================
# SET VOLUME
# ============================================================

def set_volume(percent: int) -> str:
    """
    Встановити гучність Windows від 0 до 100.

    Приклади:

    set_volume(50)
    set_volume(100)
    set_volume(0)
    """

    try:

        percent = int(percent)

    except (
        ValueError,
        TypeError,
    ):

        return "Не зрозумів рівень гучності."

    # Обмежуємо 0-100

    percent = max(
        0,
        min(
            100,
            percent,
        ),
    )

    try:

        volume = _get_volume()

        volume.SetMasterVolumeLevelScalar(
            percent / 100.0,
            None,
        )

        # Якщо ставимо 0
        if percent == 0:

            volume.SetMute(
                1,
                None,
            )

            return "Звук вимкнено."

        # Якщо було mute
        volume.SetMute(
            0,
            None,
        )

        return (
            f"Гучність встановлено "
            f"на {percent} відсотків."
        )

    except Exception as e:

        print(
            f"[system] Помилка гучності: {e}"
        )

        return "Не вдалося змінити гучність."


# ============================================================
# VOLUME UP
# ============================================================

def volume_up(step: int = 10) -> str:
    """
    Збільшити гучність.

    За замовчуванням +10%.
    """

    try:

        volume = _get_volume()

        current = (
            volume.GetMasterVolumeLevelScalar()
            * 100
        )

        new_volume = min(
            100,
            current + step,
        )

        volume.SetMasterVolumeLevelScalar(
            new_volume / 100,
            None,
        )

        volume.SetMute(
            0,
            None,
        )

        return (
            f"Гучність збільшено "
            f"до {new_volume:.0f} відсотків."
        )

    except Exception as e:

        print(
            f"[system] Помилка гучності: {e}"
        )

        return "Не вдалося збільшити гучність."


# ============================================================
# VOLUME DOWN
# ============================================================

def volume_down(step: int = 10) -> str:
    """
    Зменшити гучність.

    За замовчуванням -10%.
    """

    try:

        volume = _get_volume()

        current = (
            volume.GetMasterVolumeLevelScalar()
            * 100
        )

        new_volume = max(
            0,
            current - step,
        )

        volume.SetMasterVolumeLevelScalar(
            new_volume / 100,
            None,
        )

        if new_volume == 0:

            volume.SetMute(
                1,
                None,
            )

            return "Звук вимкнено."

        return (
            f"Гучність зменшено "
            f"до {new_volume:.0f} відсотків."
        )

    except Exception as e:

        print(
            f"[system] Помилка гучності: {e}"
        )

        return "Не вдалося зменшити гучність."


# ============================================================
# GET VOLUME
# ============================================================

def get_volume() -> str:
    """
    Показує поточну гучність.
    """

    try:

        volume = _get_volume()

        current = (
            volume.GetMasterVolumeLevelScalar()
            * 100
        )

        muted = volume.GetMute()

        if muted:

            return (
                f"Звук вимкнений. "
                f"Рівень гучності {current:.0f} відсотків."
            )

        return (
            f"Зараз гучність "
            f"{current:.0f} відсотків."
        )

    except Exception as e:

        print(
            f"[system] Помилка гучності: {e}"
        )

        return "Не вдалося отримати рівень гучності."


# ============================================================
# MUTE
# ============================================================

def mute() -> str:
    """
    Вимкнути звук.
    """

    try:

        volume = _get_volume()

        volume.SetMute(
            1,
            None,
        )

        return "Звук вимкнено."

    except Exception as e:

        print(
            f"[system] Помилка mute: {e}"
        )

        return "Не вдалося вимкнути звук."


# ============================================================
# UNMUTE
# ============================================================

def unmute() -> str:
    """
    Увімкнути звук.
    """

    try:

        volume = _get_volume()

        volume.SetMute(
            0,
            None,
        )

        return "Звук увімкнено."

    except Exception as e:

        print(
            f"[system] Помилка unmute: {e}"
        )

        return "Не вдалося увімкнути звук."


# ============================================================
# SHUTDOWN
# ============================================================

@requires_confirmation(
    description_fn=lambda:
        "Вимкнути комп'ютер зараз?"
)
def shutdown() -> str:

    subprocess.run(
        [
            "shutdown",
            "/s",
            "/t",
            "0",
        ]
    )

    return "Комп'ютер вимикається."


# ============================================================
# RESTART
# ============================================================

@requires_confirmation(
    description_fn=lambda:
        "Перезавантажити комп'ютер зараз?"
)
def restart() -> str:

    subprocess.run(
        [
            "shutdown",
            "/r",
            "/t",
            "0",
        ]
    )

    return "Комп'ютер перезавантажується."