"""
tools/apps.py

Швидке керування програмами Windows для JARVIS.

Пошук:
1. Windows special commands
2. Відомі alias
3. Відомий EXE через PATH
4. Windows App Paths
5. Start Menu shortcuts
6. Відомі стандартні директорії

ВАЖЛИВО:
- Не робимо важкий recursive search при кожній команді.
- .lnk запускаємо напряму через Windows.
"""

import os
import subprocess
import shutil
import winreg


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_name(name: str) -> str:

    if not name:
        return ""

    name = str(name).strip().lower()

    name = (
        name
        .replace("ё", "е")
        .replace("’", "'")
        .replace("`", "'")
        .replace("_", " ")
        .replace("-", " ")
    )

    if name.endswith(".exe"):
        name = name[:-4]

    name = " ".join(name.split())

    return name


# ============================================================
# ALIASES
# ============================================================

APP_ALIASES = {

    # ========================================================
    # TELEGRAM
    # ========================================================

    "телеграм": "telegram",
    "телеграмм": "telegram",
    "телега": "telegram",
    "telegram": "telegram",

    # ========================================================
    # STEAM
    # ========================================================

    "стим": "steam",
    "стім": "steam",
    "стімм": "steam",
    "стимм": "steam",
    "стіам": "steam",

    # Помилки Azure Speech
    "тим": "steam",
    "тім": "steam",
    "в тим": "steam",
    "в тім": "steam",
    "включи тим": "steam",
    "включи тім": "steam",
    "включить тим": "steam",
    "включить тім": "steam",

    "steam": "steam",

    # ========================================================
    # CHROME
    # ========================================================

    "кром": "chrome",
    "хром": "chrome",
    "гугл хром": "chrome",
    "гуглхром": "chrome",
    "chrome": "chrome",

    # ========================================================
    # DISCORD
    # ========================================================

    "дискорд": "discord",
    "дис": "discord",
    "дс": "discord",
    "discord": "discord",

    # ========================================================
    # FIREFOX
    # ========================================================

    "фаерфокс": "firefox",
    "файрфокс": "firefox",
    "фаєрфокс": "firefox",
    "firefox": "firefox",

    # ========================================================
    # VS CODE
    # ========================================================

    "вс код": "vs code",
    "вскод": "vs code",
    "вс-код": "vs code",
    "візуал студіо код": "vs code",
    "visual studio code": "vs code",
    "vs code": "vs code",

    # ========================================================
    # EXPLORER
    # ========================================================

    "проводник": "explorer",
    "провідник": "explorer",
    "explorer": "explorer",

    # ========================================================
    # CALCULATOR
    # ========================================================

    "калькулятор": "calculator",
    "калькулятор виндовс": "calculator",
    "calculator": "calculator",

    # ========================================================
    # NOTEPAD
    # ========================================================

    "блокнот": "notepad",
    "нотатник": "notepad",
    "notepad": "notepad",
}
# ============================================================
# PROCESS NAMES
# ============================================================

PROCESS_NAMES = {

    "telegram": [
        "Telegram.exe"
    ],

    "steam": [
        "steam.exe"
    ],

    "teams": [
        "ms-teams.exe",
        "Teams.exe"
    ],

    "chrome": [
        "chrome.exe"
    ],

    "firefox": [
        "firefox.exe"
    ],

    "discord": [
        "Discord.exe"
    ],

    "vs code": [
        "Code.exe"
    ],

    "explorer": [
        "explorer.exe"
    ],

    "calculator": [
        "CalculatorApp.exe",
        "Calculator.exe"
    ],

    "notepad": [
        "notepad.exe"
    ],
}


# ============================================================
# SPECIAL WINDOWS COMMANDS
# ============================================================

SPECIAL_COMMANDS = {

    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "explorer": "explorer.exe",
}


# ============================================================
# DISPLAY NAMES
# ============================================================

DISPLAY_NAMES = {

    "telegram": "Telegram",
    "steam": "Steam",
    "teams": "Microsoft Teams",
    "chrome": "Chrome",
    "firefox": "Firefox",
    "discord": "Discord",
    "vs code": "VS Code",
    "explorer": "Провідник",
    "calculator": "Калькулятор",
    "notepad": "Блокнот",
}


# ============================================================
# START MENU
# ============================================================

START_MENU_ROOTS = [

    os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs"
    ),

    os.path.join(
        os.environ.get("ProgramData", ""),
        r"Microsoft\Windows\Start Menu\Programs"
    ),
]


# ============================================================
# KNOWN DIRECT PATHS
# ============================================================

KNOWN_PATHS = {

    "steam": [
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
    ],

    "telegram": [
        os.path.expandvars(
            r"%APPDATA%\Telegram Desktop\Telegram.exe"
        ),
    ],

    "chrome": [
        os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
        ),

        os.path.expandvars(
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
        ),

        os.path.expandvars(
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
        ),
    ],

    "firefox": [
        os.path.expandvars(
            r"%ProgramFiles%\Mozilla Firefox\firefox.exe"
        ),

        os.path.expandvars(
            r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"
        ),
    ],

    "discord": [
        os.path.expandvars(
            r"%LOCALAPPDATA%\Discord\Update.exe"
        ),
    ],

    "vs code": [
        os.path.expandvars(
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"
        ),

        os.path.expandvars(
            r"%ProgramFiles%\Microsoft VS Code\Code.exe"
        ),
    ],
}


# ============================================================
# ALIAS
# ============================================================

def _resolve_alias(name: str) -> str:

    name = _normalize_name(name)

    return APP_ALIASES.get(
        name,
        name
    )


# ============================================================
# PATH
# ============================================================

def _find_via_path(exe_name: str):

    if not exe_name:
        return None

    try:

        path = shutil.which(exe_name)

        if path and os.path.isfile(path):
            return path

    except Exception:
        pass

    return None


# ============================================================
# APP PATHS
# ============================================================

def _find_via_app_paths(exe_name: str):

    if not exe_name:
        return None

    key_path = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion"
        rf"\App Paths\{exe_name}"
    )

    for hive in (
        winreg.HKEY_CURRENT_USER,
        winreg.HKEY_LOCAL_MACHINE,
    ):

        for view in (
            winreg.KEY_WOW64_64KEY,
            winreg.KEY_WOW64_32KEY,
        ):

            try:

                with winreg.OpenKey(
                    hive,
                    key_path,
                    0,
                    winreg.KEY_READ | view
                ) as key:

                    value, _ = winreg.QueryValueEx(
                        key,
                        None
                    )

                    if value:

                        value = str(value).strip('"')

                        if os.path.isfile(value):
                            return value

            except (
                FileNotFoundError,
                OSError
            ):
                continue

    return None


# ============================================================
# STEAM REGISTRY
# ============================================================

def _find_steam_via_registry():
    """
    Steam завжди пише свій реальний шлях встановлення
    в реєстр. Це найнадійніший спосіб знайти steam.exe
    незалежно від того, на якому диску він встановлений.
    """

    try:

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Valve\Steam"
        ) as key:

            install_path, _ = winreg.QueryValueEx(
                key,
                "SteamPath"
            )

            exe = os.path.join(
                install_path.replace("/", "\\"),
                "steam.exe"
            )

            if os.path.isfile(exe):
                return exe

    except (FileNotFoundError, OSError):
        pass

    try:

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Valve\Steam"
        ) as key:

            install_path, _ = winreg.QueryValueEx(
                key,
                "InstallPath"
            )

            exe = os.path.join(
                install_path,
                "steam.exe"
            )

            if os.path.isfile(exe):
                return exe

    except (FileNotFoundError, OSError):
        pass

    return None


# ============================================================
# START MENU
# ============================================================

def _find_via_start_menu(app_name: str):

    target = _normalize_name(
        app_name
    )

    if not target:
        return None

    for root in START_MENU_ROOTS:

        if not os.path.isdir(root):
            continue

        try:

            for current_root, dirs, files in os.walk(root):

                # Не йдемо в непотрібну глибину
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".")
                ]

                for filename in files:

                    lower = filename.lower()

                    if not (
                        lower.endswith(".lnk")
                        or lower.endswith(".url")
                    ):
                        continue

                    filename_without_ext = os.path.splitext(
                        filename
                    )[0]

                    normalized = _normalize_name(
                        filename_without_ext
                    )

                    if (
                        normalized == target
                        or target in normalized
                        or normalized in target
                    ):

                        return os.path.join(
                            current_root,
                            filename
                        )

        except Exception:
            continue

    return None


# ============================================================
# SPECIAL WINDOWS PROGRAM
# ============================================================

def _find_special(app_name: str):

    command = SPECIAL_COMMANDS.get(
        app_name
    )

    if not command:
        return None

    path = shutil.which(command)

    if path:
        return path

    return None


# ============================================================
# KNOWN PATHS
# ============================================================

def _find_known_path(app_name: str):

    paths = KNOWN_PATHS.get(
        app_name,
        []
    )

    for path in paths:

        if not path:
            continue

        path = os.path.expandvars(path)

        if os.path.isfile(path):
            return path

    return None


# ============================================================
# FIND APP
# ============================================================

def find_app(name: str):

    original_name = name

    app_name = _resolve_alias(
        name
    )

    if not app_name:

        print(
            "[apps] Порожня назва програми."
        )

        return None

    print(
        f"[apps] Пошук: {original_name} -> {app_name}"
    )

    # ========================================================
    # 1. SPECIAL WINDOWS
    # ========================================================

    path = _find_special(
        app_name
    )

    if path:

        print(
            f"[apps] Windows: {path}"
        )

        return path

    # ========================================================
    # 1.5. STEAM REGISTRY
    # ========================================================

    if app_name == "steam":

        path = _find_steam_via_registry()

        if path:

            print(
                f"[apps] Steam registry: {path}"
            )

            return path

    # ========================================================
    # 2. KNOWN PATH
    # ========================================================

    path = _find_known_path(
        app_name
    )

    if path:

        print(
            f"[apps] Відомий шлях: {path}"
        )

        return path

    # ========================================================
    # 3. KNOWN PROCESS EXE
    # ========================================================

    process_names = PROCESS_NAMES.get(
        app_name,
        []
    )

    for exe_name in process_names:

        path = _find_via_path(
            exe_name
        )

        if path:

            print(
                f"[apps] PATH: {path}"
            )

            return path

        path = _find_via_app_paths(
            exe_name
        )

        if path:

            print(
                f"[apps] App Paths: {path}"
            )

            return path

    # ========================================================
    # 4. START MENU
    # ========================================================

    path = _find_via_start_menu(
        app_name
    )

    if path:

        print(
            f"[apps] Start Menu: {path}"
        )

        return path

    # ========================================================
    # 5. НЕ ЗНАЙДЕНО
    # ========================================================

    print(
        f"[apps] Не знайдено: {original_name}"
    )

    return None


# ============================================================
# OPEN APP
# ============================================================

def open_app(name: str) -> str:

    app_name = _resolve_alias(
        name
    )

    path = find_app(
        app_name
    )

    if not path:

        return (
            f"Не знайшов {name}. "
            f"Перевір, чи програма встановлена."
        )

    display_name = DISPLAY_NAMES.get(
        app_name,
        name
    )

    # ========================================================
    # URL
    # ========================================================

    if (
        path.startswith("http://")
        or path.startswith("https://")
    ):

        try:

            os.startfile(path)

            return (
                f"Готово. "
                f"{display_name} відкрито."
            )

        except Exception as e:

            print(
                f"[apps] URL error: {e}"
            )

            return (
                f"Не вдалося відкрити "
                f"{display_name}."
            )

    # ========================================================
    # START MENU SHORTCUT
    # ========================================================

    if path.lower().endswith(
        (".lnk", ".url")
    ):

        try:

            os.startfile(path)

            print(
                f"[apps] Відкрито ярлик: {path}"
            )

            return (
                f"Готово. "
                f"{display_name} відкрито."
            )

        except Exception as e:

            print(
                f"[apps] Помилка ярлика: {e}"
            )

            return (
                f"Не вдалося відкрити "
                f"{display_name}."
            )

    # ========================================================
    # EXE
    # ========================================================

    try:

        subprocess.Popen(
            [path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        print(
            f"[apps] Відкрито: {display_name}"
        )

        print(
            f"[apps] Шлях: {path}"
        )

        return (
            f"Готово. "
            f"{display_name} відкрито."
        )

    except Exception as e:

        print(
            f"[apps] Помилка запуску: {e}"
        )

        return (
            f"Не вдалося запустити "
            f"{display_name}."
        )


# ============================================================
# CLOSE APP
# ============================================================

def close_app(name: str) -> str:

    app_name = _resolve_alias(
        name
    )

    display_name = DISPLAY_NAMES.get(
        app_name,
        name
    )

    print(
        f"[apps] Закриваю: {app_name}"
    )

    process_names = PROCESS_NAMES.get(
        app_name,
        []
    )

    for process_name in process_names:

        try:

            result = subprocess.run(
                [
                    "taskkill",
                    "/IM",
                    process_name,
                    "/F"
                ],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:

                print(
                    f"[apps] Закрито: {process_name}"
                )

                return (
                    f"Готово. "
                    f"{display_name} закрито."
                )

        except Exception as e:

            print(
                f"[apps] taskkill error: {e}"
            )

    return (
        f"Не вдалося закрити "
        f"{display_name}. "
        f"Можливо, програма не запущена."
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("JARVIS APP SEARCH TEST")
    print("=" * 60)

    for app in (
        "telegram",
        "телеграм",
        "steam",
        "стім",
        "тім",
        "teams",
        "калькулятор",
        "chrome",
        "discord",
    ):

        print()
        print(f"TEST: {app}")

        result = find_app(app)

        print(
            f"RESULT: {result}"
        )