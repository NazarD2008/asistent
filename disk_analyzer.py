
from pathlib import Path

# Скільки найбільших папок показувати
TOP_FOLDERS = 20

# Що скануємо
ROOT = Path("C:\\")


from pathlib import Path

from size_utils import get_size, bytes_to_gb

TOP_FOLDERS = 20
ROOT = Path("C:\\")


def analyze_disk():
    print("=" * 60)
    print("             JARVIS DISK ANALYZER")
    print("=" * 60)

    print("\n🔎 Сканую диск C:\\")
    print("⏳ Це може зайняти кілька хвилин...\n")

    folders = []

    try:
        items = list(ROOT.iterdir())
    except PermissionError:
        print("❌ Немає доступу до диска C:\\")
        return

    for item in items:

        if not item.is_dir():
            continue

        if item.name in [
            "$Recycle.Bin",
            "System Volume Information"
        ]:
            continue

        print(f"📂 Аналізую: {item}")

        size = get_size(item)

        folders.append((size, item))

    folders.sort(reverse=True, key=lambda x: x[0])

    print("\n")
    print("=" * 60)
    print("             НАЙБІЛЬШІ ПАПКИ")
    print("=" * 60)

    for index, (size, folder) in enumerate(
        folders[:TOP_FOLDERS],
        start=1
    ):
        print(
            f"{index:>2}. "
            f"{bytes_to_gb(size):>8.2f} GB   "
            f"{folder}"
        )

    print("\n" + "=" * 60)
    print("          ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    analyze_disk()