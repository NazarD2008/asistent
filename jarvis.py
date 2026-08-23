import psutil
import platform
import os

from datetime import datetime

from agent.agent import process


# ============================================================
# SYSTEM INFO
# ============================================================

def bytes_to_gb(value):
    return round(value / (1024 ** 3), 2)


def get_system_info():
    print("\n" + "=" * 50)
    print("          JARVIS PC ANALYSIS")
    print("=" * 50)

    print(f"\n🖥️ Комп'ютер: {platform.node()}")
    print(f"💻 Система: {platform.system()} {platform.release()}")
    print(f"⚙️ Процесор: {platform.processor()}")

    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()

    print(f"\n🧠 CPU: {cpu}%")

    print(
        f"🧠 RAM: {bytes_to_gb(ram.used)} / "
        f"{bytes_to_gb(ram.total)} GB "
        f"({ram.percent}%)"
    )

    print("\n💾 Диски:")

    for partition in psutil.disk_partitions():

        try:

            usage = psutil.disk_usage(
                partition.mountpoint
            )

            print(
                f"   {partition.mountpoint} "
                f"{bytes_to_gb(usage.used)} / "
                f"{bytes_to_gb(usage.total)} GB "
                f"({usage.percent}%)"
            )

        except PermissionError:
            pass

    print("\n⚡ Найбільш навантажені процеси:")

    processes = []

    for proc in psutil.process_iter(
        ["pid", "name", "cpu_percent", "memory_percent"]
    ):

        try:

            info = proc.info

            processes.append(
                (
                    info["cpu_percent"] or 0,
                    info["memory_percent"] or 0,
                    info["name"] or "Unknown",
                    info["pid"],
                )
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied
        ):

            pass

    processes.sort(reverse=True)

    for cpu_usage, memory_usage, name, pid in processes[:10]:

        print(
            f"   PID {pid:<6} "
            f"CPU {cpu_usage:>5.1f}% "
            f"RAM {memory_usage:>5.1f}% "
            f"{name}"
        )

    print("\n🌐 Мережа:")

    network = psutil.net_io_counters()

    print(
        f"   ↑ Відправлено: "
        f"{bytes_to_gb(network.bytes_sent)} GB"
    )

    print(
        f"   ↓ Отримано:    "
        f"{bytes_to_gb(network.bytes_recv)} GB"
    )

    print(
        "\n🕐 Час аналізу:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("\n" + "=" * 50)
    print("          ANALYSIS COMPLETE")
    print("=" * 50)


# ============================================================
# COMMAND CONTROL
# ============================================================

EXIT_COMMANDS = {
    "вихід",
    "вийти",
    "стоп",
    "exit",
    "quit",
}


CANCEL_FOLLOW_UP_COMMANDS = {
    "це все",
    "досить",
    "все",
    "скасовуй",
    "скасувати",
    "відміна",
    "відміни",
    "не треба",
    "не потрібно",
    "дякую",
}


# ============================================================
# DISPATCH
# ============================================================

def _dispatch(command: str) -> str:

    low = command.lower().strip()

    # --------------------------------------------------------
    # Аналіз ПК
    # --------------------------------------------------------

    if low in (
        "аналіз",
        "аналіз пк",
        "аналіз системи",
        "проаналізуй пк",
        "проаналізуй комп'ютер",
        "покажи стан пк",
    ):

        get_system_info()

        return "Готово."

    # --------------------------------------------------------
    # Все інше -> Agent
    # --------------------------------------------------------

    return process(command)


# ============================================================
# VOICE LOOP
# ============================================================

def voice_loop():

    from voice import listen_for_command, speak, voice_confirm
    from permissions import set_confirm_handler

    set_confirm_handler(voice_confirm)

    speak(
        "Готовий до роботи."
    )


    # Follow-up режим
    #
    # False = потрібен wake word
    # True  = wake word не потрібен
    # --------------------------------------------------------

    follow_up = False

    while True:

        # ====================================================
        # СЛУХАЄМО
        # ====================================================

        command = listen_for_command(
            require_wake_word=not follow_up
        )

        # --------------------------------------------------------
        # Follow-up закінчився без нової команди
        # --------------------------------------------------------

        if not command:

            if follow_up:
                print(
                    "[agent] Повертаюсь "
                    "до режиму wake word."
                )

                follow_up = False

                continue

            continue

        command = command.strip()

        if not command:
            continue

        print(
            f"Ти (голосом): {command}"
        )

        low = command.lower().strip()
        # ====================================================
        # ПОВНИЙ ВИХІД
        # ====================================================

        if low in EXIT_COMMANDS:
            speak(
                "До зустрічі."
            )

            break
        # ====================================================
        # СКАСУВАННЯ FOLLOW-UP
        # ====================================================

        if (
            follow_up
            and
            low in CANCEL_FOLLOW_UP_COMMANDS
        ):

            print(
                "[agent] Follow-up "
                "скасовано користувачем."
            )

            speak(
                "Добре."
            )

            follow_up = False

            continue


        # ====================================================
        # ВИКОНАННЯ КОМАНДИ
        # ====================================================

        response = _dispatch(
            command
        )

        if response:
            speak(
                response
            )
        # ====================================================
        # FOLLOW-UP
        # ====================================================

        follow_up = True

        print(
            "[agent] Follow-up режим активовано."
        )

        print(
            "[agent] Наступну команду можна "
            "сказати без wake word.")

# ============================================================
# TEXT LOOP
# ============================================================

def text_loop():

    print(
        "Скажи команду "
        "('аналіз' — повний звіт по ПК, "
        "'вихід' — завершити)."
    )

    while True:

        command = input(
            "\nТи: "
        ).strip()

        if not command:
            continue

        low = command.lower()

        if low in EXIT_COMMANDS:

            print(
                "JARVIS: До зустрічі."
            )

            break

        response = _dispatch(
            command
        )

        print(
            f"JARVIS: {response}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "JARVIS готовий."
    )

    mode = input(
        "Обери режим: "
        "[1] голосом  "
        "[2] текстом "
        "(Enter = текстом): "
    ).strip()

    if mode == "1":

        voice_loop()

    else:

        text_loop()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()