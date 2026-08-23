import sys
from pathlib import Path

from size_utils import get_size, bytes_to_gb

TOP_ITEMS = 30


def analyze_folder(folder):
    folder = Path(folder)

    if not folder.exists():
        print(f"❌ Папку не знайдено: {folder}")
        return

    print("=" * 65)
    print("              JARVIS FOLDER ANALYZER")
    print("=" * 65)

    print(f"\n📂 Сканую: {folder}")
    print("⏳ Зачекай, це може зайняти деякий час...\n")

    items = []

    try:
        children = list(folder.iterdir())
    except PermissionError:
        print("❌ Немає доступу до цієї папки.")
        return

    for item in children:

        print(f"🔎 {item}")

        try:
            if item.is_file():
                size = item.stat().st_size
            else:
                size = get_size(item)

            items.append((size, item))

        except (PermissionError, FileNotFoundError, OSError):
            pass

    items.sort(reverse=True, key=lambda x: x[0])

    print("\n")
    print("=" * 65)
    print("              НАЙБІЛЬШІ ОБ'ЄКТИ")
    print("=" * 65)

    for index, (size, item) in enumerate(
        items[:TOP_ITEMS],
        start=1
    ):
        item_type = "📁" if item.is_dir() else "📄"

        print(
            f"{index:>2}. "
            f"{bytes_to_gb(size):>8.2f} GB   "
            f"{item_type} {item}"
        )

    print("\n" + "=" * 65)
    print("              ANALYSIS COMPLETE")
    print("=" * 65)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Вкажи папку для аналізу.")
        print()
        print("Приклад:")
        print("python folder_analyzer.py C:\\Users")
        sys.exit()

    analyze_folder(sys.argv[1])