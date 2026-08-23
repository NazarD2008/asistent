import re
import psutil
import platform
import os

from datetime import datetime

from agent.agent import process


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
    print(f"🧠 RAM: {bytes_to_gb(ram.used)} / {bytes_to_gb(ram.total)} GB ({ram.percent}%)")
    print("\n💾 Диски:")
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            print(f"   {partition.mountpoint} {bytes_to_gb(usage.used)} / {bytes_to_gb(usage.total)} GB ({usage.percent}%)")
        except PermissionError:
            pass
    print("\n⚡ Найбільш навантажені процеси:")
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            processes.append((info["cpu_percent"] or 0, info["memory_percent"] or 0, info["name"] or "Unknown", info["pid"]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    processes.sort(reverse=True)
    for cpu_usage, memory_usage, name, pid in processes[:10]:
        print(f"   PID {pid:<6} CPU {cpu_usage:>5.1f}% RAM {memory_usage:>5.1f}% {name}")
    network = psutil.net_io_counters()
    print("\n🌐 Мережа:")
    print(f"   ↑ Відправлено: {bytes_to_gb(network.bytes_sent)} GB")
    print(f"   ↓ Отримано:    {bytes_to_gb(network.bytes_recv)} GB")
    print("\n🕐 Час аналізу:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("\n" + "=" * 50)
    print("          ANALYSIS COMPLETE")
    print("=" * 50)


EXIT_COMMANDS = {"вихід", "вийти", "стоп", "exit", "quit"}
CANCEL_FOLLOW_UP_COMMANDS = {"це все", "досить", "все", "скасовуй", "скасувати", "відміна", "відміни", "не треба", "не потрібно", "дякую"}


def _dispatch(command: str) -> str:
    low = command.lower().strip()
    if low in ("аналіз", "аналіз пк", "аналіз системи", "проаналізуй пк", "проаналізуй комп'ютер", "покажи стан пк"):
        get_system_info()
        return "Готово."
    return process(command)


def _voice_response(text: str) -> str:
    """Перетворює технічний/довгий результат на нормальну коротку репліку для TTS."""
    if not text:
        return ""

    value = str(text).strip()
    low = value.lower()

    if low.startswith("знайшов файли:") or low.startswith("знайшов кілька файлів:"):
        return "Знайшов кілька файлів. Скажи номер потрібного."

    if low.startswith("знайшов папки:"):
        return "Знайшов кілька папок. Скажи номер потрібної."

    if low.startswith("скріншот збережено:"):
        return "Скріншот готовий."

    value = re.sub(r"[A-Za-z]:\\[^\n]+", "", value)
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"\s+", " ", value).strip()

    # Не змушуємо TTS читати довгі vision/web результати.
    if len(value) > 320:
        sentences = re.split(r"(?<=[.!?])\s+", value)
        value = " ".join(sentences[:2]).strip()

    if len(value) > 320:
        value = value[:317].rstrip() + "..."

    return value


def voice_loop():
    from voice import listen_for_command, speak, voice_confirm
    from permissions import set_confirm_handler
    set_confirm_handler(voice_confirm)
    speak("Готовий до роботи.")
    follow_up = False

    while True:
        command = listen_for_command(require_wake_word=not follow_up)
        if not command:
            if follow_up:
                print("[agent] Повертаюсь до режиму wake word.")
                follow_up = False
            continue

        command = command.strip()
        if not command:
            continue

        print(f"Ти (голосом): {command}")
        low = command.lower().strip()

        if low in EXIT_COMMANDS:
            speak("До зустрічі.")
            break

        if follow_up and low in CANCEL_FOLLOW_UP_COMMANDS:
            print("[agent] Follow-up скасовано користувачем.")
            speak("Добре.")
            follow_up = False
            continue

        response = _dispatch(command)
        if response:
            speak(_voice_response(response))

        follow_up = True
        print("[agent] Follow-up режим активовано.")
        print("[agent] Наступну команду можна сказати без wake word.")


def text_loop():
    print("Скажи команду ('аналіз' — повний звіт по ПК, 'вихід' — завершити).")
    while True:
        command = input("\nТи: ").strip()
        if not command:
            continue
        if command.lower() in EXIT_COMMANDS:
            print("JARVIS: До зустрічі.")
            break
        response = _dispatch(command)
        print(f"JARVIS: {response}")


def main():
    print("JARVIS готовий.")
    mode = input("Обери режим: [1] голосом  [2] текстом (Enter = текстом): ").strip()
    if mode == "1":
        voice_loop()
    else:
        text_loop()


if __name__ == "__main__":
    main()
