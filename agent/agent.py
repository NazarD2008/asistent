"""
JARVIS Agent Core

Єдиний центральний шар JARVIS.

Відповідає за:
- отримання команди;
- локальне визначення простої команди через router;
- передачу складної команди в brain;
- єдине виконання action через tools;
- пам'ять і контекст;
- follow-up режим.

Архітектура:

command
   ↓
Agent
   ├── Router → action/target
   └── Brain  → action/target
            ↓
         Executor
            ↓
          Tools
"""

from command_router import route
from brain import handle

from .memory import Memory


# ============================================================
# AGENT
# ============================================================

class JarvisAgent:

    def __init__(self):

        self.memory = Memory()

        self.follow_up_active = False

        self.last_action = None
        self.last_target = None

    # ========================================================
    # PROCESS
    # ========================================================

    def process(self, command: str) -> str:

        if not command or not command.strip():
            return "Я не почув команду."

        command = command.strip()

        print(
            f"[agent] Команда: {command}"
        )

        try:

            normalized = (
                command
                .lower()
                .strip()
                .replace("ё", "е")
            )

            # =================================================
            # STOP
            # =================================================

            if normalized in (
                "стоп",
                "вихід",
                "вийти",
                "exit",
                "quit",
            ):

                self.follow_up_active = False

                response = "До зустрічі."

                self.last_action = "stop"
                self.last_target = ""

                self.memory.remember(
                    command,
                    response,
                    action="stop",
                    target="",
                )

                return response

            # =================================================
            # 1. LOCAL ROUTER
            # =================================================

            decision = route(
                command,
                context=self.memory.context(),
            )

            # =================================================
            # 2. BRAIN / GPT
            # =================================================

            if decision is None:

                context = self.memory.context()

                print(
                    f"[agent] Контекст: {context}"
                )

                decision = handle(
                    command,
                    context=context,
                )

            # =================================================
            # VALIDATE DECISION
            # =================================================

            if not isinstance(decision, dict):

                raise TypeError(
                    "Brain/Router повинні повертати dict."
                )

            action = decision.get(
                "action",
                "unknown",
            )

            target = str(
                decision.get(
                    "target",
                    "",
                )
                or ""
            ).strip()

            # =================================================
            # EXECUTE
            # =================================================

            response = self.execute(
                action,
                target,
                command,
            )

            response = str(
                response or ""
            ).strip()

            # =================================================
            # SAVE STATE
            # =================================================

            self.last_action = action
            self.last_target = target

            self.memory.remember(
                command,
                response,
                action=action,
                target=target,
            )

            print(
                f"[agent] Action: {action}"
            )

            print(
                f"[agent] Target: {target}"
            )

            print(
                f"[agent] Відповідь: {response}"
            )

            return response

        except Exception as e:

            print(
                f"[agent] ПОМИЛКА: {e}"
            )

            response = (
                "Сталася помилка "
                "під час обробки команди."
            )

            self.last_action = "error"
            self.last_target = ""

            self.memory.remember(
                command,
                response,
                action="error",
                target="",
            )

            return response

    # ========================================================
    # EXECUTOR
    # ========================================================

    def execute(
        self,
        action: str,
        target: str = "",
        command: str = "",
    ) -> str:
        """
        Єдине місце виконання action.

        Brain і Router тільки визначають ДІЮ.
        Agent визначає, ЯК її виконати.
        """

        action = action or "unknown"
        target = target or ""

        print(
            f"[agent] Execute: {action}"
        )

        print(
            f"[agent] Execute target: {target}"
        )

        # ====================================================
        # APPS
        # ====================================================

        if action == "open_app":

            from tools import apps

            return apps.open_app(target)

        if action == "close_app":

            from tools import apps

            return apps.close_app(target)

        # ====================================================
        # BROWSER / MEDIA
        # ====================================================

        if action == "play_video":

            from tools import browser

            result = browser.play_video(target)

            if browser.has_last_results():

                results = browser.get_last_results()

                return (
                    f"Знайшов {len(results)} відео. "
                    f"Яке відкрити?"
                )

            return result

        if action == "open_video_result":

            from tools import browser

            try:
                number = int(target.strip())
            except (ValueError, TypeError):
                return "Не зрозумів номер відео."

            return browser.open_video_number(number)

        if action == "play_music":

            from tools import browser

            return browser.play_music(target)

        if action == "find_movie":

            from tools import browser

            return browser.find_movie(target)

        if action == "open_url":

            from tools import browser

            return browser.open_url(target)

        if action == "web_search":

            from tools import browser

            if not target:
                return "Не вказаний пошуковий запит."

            import urllib.parse

            search_url = (
                "https://www.google.com/search?q="
                + urllib.parse.quote(target)
            )

            return browser.open_url(search_url)

        # ====================================================
        # SYSTEM
        # ====================================================

        if action == "analyze_memory":

            try:
                from disk_analyzer import analyze_memory

                return str(
                    analyze_memory()
                )

            except Exception as e:

                print(
                    f"[agent] Memory analysis error: {e}"
                )

                return (
                    "Не вдалося проаналізувати "
                    "пам'ять комп'ютера."
                )

        if action in (
            "set_volume",
            "volume_up",
            "volume_down",
            "mute",
            "unmute",
        ):

            try:
                from tools import system

                function = getattr(
                    system,
                    action,
                )

                if target:
                    return str(
                        function(target)
                    )

                return str(
                    function()
                )

            except Exception as e:

                print(
                    f"[agent] System audio error: {e}"
                )

                return (
                    "Не вдалося змінити гучність."
                )

        if action == "shutdown":

            try:
                from tools import system
                from permissions import ActionCancelled

                return system.shutdown()

            except ActionCancelled:

                return "Добре, скасовано."

            except Exception as e:

                print(
                    f"[agent] Shutdown error: {e}"
                )

                return (
                    "Не вдалося вимкнути комп'ютер."
                )

        if action == "restart":

            try:
                from tools import system
                from permissions import ActionCancelled

                return system.restart()

            except ActionCancelled:

                return "Добре, скасовано."

            except Exception as e:

                print(
                    f"[agent] Restart error: {e}"
                )

                return (
                    "Не вдалося перезавантажити комп'ютер."
                )

        # ====================================================
        # CHAT
        # ====================================================

        if action == "chat":

            return target or "Так, слухаю."

        # ====================================================
        # STOP
        # ====================================================

        if action == "stop":

            self.follow_up_active = False

            return "До зустрічі."

        # ====================================================
        # UNKNOWN
        # ====================================================

        return "Не зовсім зрозумів команду."

    # ========================================================
    # FOLLOW-UP
    # ========================================================

    def set_follow_up(self, active: bool):

        self.follow_up_active = bool(active)

        if self.follow_up_active:

            print(
                "[agent] Follow-up режим активовано."
            )

        else:

            print(
                "[agent] Режим wake word."
            )

    def is_follow_up_active(self):

        return self.follow_up_active

    # ========================================================
    # CONTEXT
    # ========================================================

    def get_context(self):

        return self.memory.context()

    # ========================================================
    # LAST COMMAND
    # ========================================================

    def get_last_command(self):

        return self.memory.last_command

    # ========================================================
    # LAST RESULT
    # ========================================================

    def get_last_result(self):

        return self.memory.last_result

    # ========================================================
    # LAST ACTION
    # ========================================================

    def get_last_action(self):

        return self.last_action

    # ========================================================
    # LAST TARGET
    # ========================================================

    def get_last_target(self):

        return self.last_target

    # ========================================================
    # CLEAR MEMORY
    # ========================================================

    def clear_memory(self):

        self.memory.clear()

        self.follow_up_active = False

        self.last_action = None
        self.last_target = None

        print(
            "[agent] Пам'ять очищено."
        )


# ============================================================
# GLOBAL AGENT
# ============================================================

agent = JarvisAgent()


# ============================================================
# PUBLIC API
# ============================================================

def process(command: str) -> str:

    return agent.process(command)


def set_follow_up(active: bool):

    agent.set_follow_up(active)


def is_follow_up_active():

    return agent.is_follow_up_active()
