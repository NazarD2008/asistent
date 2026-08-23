"""JARVIS Agent Core."""

from command_router import route
from brain import handle
from .memory import Memory


class JarvisAgent:
    def __init__(self):
        self.memory = Memory()
        self.follow_up_active = False
        self.last_action = None
        self.last_target = None

    def _numeric_file_follow_up(self, command: str):
        """Якщо попередня команда дала список файлів, число вибирає файл."""
        normalized = command.lower().strip()
        if not normalized.isdigit():
            return None
        if self.last_action != "open_file":
            return None

        from tools import files
        return files.open_file_number(int(normalized))

    def _resolve_follow_up(self, command: str, action: str, target: str):
        normalized = command.lower().strip().replace("ё", "е")
        words = normalized.split()

        if action == "open_video_result" or any(
            phrase in normalized
            for phrase in ("перше відео", "друге відео", "третє відео", "перше", "друге", "третє")
        ):
            from tools import browser
            if browser.has_last_results():
                if action == "open_video_result":
                    try:
                        return "open_video_result", str(int(target))
                    except (ValueError, TypeError):
                        pass
                numbers = {"перше": 1, "друге": 2, "третє": 3}
                for word, number in numbers.items():
                    if word in words:
                        return "open_video_result", str(number)
                for word in words:
                    if word.isdigit():
                        return "open_video_result", word

        reference_words = ("його", "її", "це", "цей", "цю", "там", "той", "те")
        has_reference = any(word in normalized for word in reference_words)

        if action == "close_app" and not target and self.last_action == "open_app":
            return "close_app", self.last_target or ""

        if has_reference and self.last_target:
            if action in ("close_app", "open_app") and self.last_action in ("open_app", "close_app"):
                return action, self.last_target
            if action == "find_content" and self.last_action == "find_content":
                return action, self.last_target
            if action == "play_music" and self.last_action == "play_music":
                return action, self.last_target

        return action, target

    def process(self, command: str) -> str:
        if not command or not command.strip():
            return "Я не почув команду."

        command = command.strip()
        print(f"[agent] Команда: {command}")

        try:
            normalized = command.lower().strip().replace("ё", "е")

            if normalized in ("стоп", "вихід", "вийти", "exit", "quit"):
                self.follow_up_active = False
                response = "До зустрічі."
                self.last_action = "stop"
                self.last_target = ""
                self.memory.remember(command, response, action="stop", target="")
                return response

            # Число після "відкрий файл ..." вибирає пункт зі списку.
            if normalized.isdigit() and self.last_action == "open_file":
                response = self._numeric_file_follow_up(normalized)
                self.last_target = ""
                self.memory.remember(command, response, action="open_file_number", target=normalized)
                print(f"[agent] Action: open_file_number")
                print(f"[agent] Target: {normalized}")
                print(f"[agent] Відповідь: {response}")
                return response

            decision = route(command, context=self.memory.context())

            if decision is None:
                context = self.memory.context()
                print(f"[agent] Контекст: {context}")
                decision = handle(command, context=context)

            if not isinstance(decision, dict):
                raise TypeError("Brain/Router повинні повертати dict.")

            action = decision.get("action", "unknown")
            target = str(decision.get("target", "") or "").strip()
            action, target = self._resolve_follow_up(command, action, target)

            response = str(self.execute(action, target, command) or "").strip()

            self.last_action = action
            self.last_target = target
            self.memory.remember(command, response, action=action, target=target)

            print(f"[agent] Action: {action}")
            print(f"[agent] Target: {target}")
            print(f"[agent] Відповідь: {response}")
            return response

        except Exception as e:
            print(f"[agent] ПОМИЛКА: {e}")
            response = "Сталася помилка під час обробки команди."
            self.last_action = "error"
            self.last_target = ""
            self.memory.remember(command, response, action="error", target="")
            return response

    def execute(self, action: str, target: str = "", command: str = "") -> str:
        action = action or "unknown"
        target = target or ""
        print(f"[agent] Execute: {action}")
        print(f"[agent] Execute target: {target}")

        if action in ("find_file", "open_file", "delete_file", "find_folder"):
            from tools import files
            function = getattr(files, action)
            return str(function(target))

        if action == "open_path":
            from tools import files
            return str(files.open_path(target))

        if action == "open_app":
            from tools import apps
            return apps.open_app(target)

        if action == "close_app":
            from tools import apps
            return apps.close_app(target)

        if action == "play_video":
            from tools import browser
            result = browser.play_video(target)
            if browser.has_last_results():
                return f"Знайшов {len(browser.get_last_results())} відео. Яке відкрити?"
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

        if action == "find_content":
            from tools import browser
            return browser.find_content(target)

        if action == "open_url":
            from tools import browser
            return browser.open_url(target)

        if action == "web_search":
            from tools import browser
            if not target:
                return "Не вказаний пошуковий запит."
            import urllib.parse
            search_url = "https://www.google.com/search?q=" + urllib.parse.quote(target)
            return browser.open_url(search_url)

        if action == "analyze_memory":
            try:
                from disk_analyzer import analyze_memory
                return str(analyze_memory())
            except Exception as e:
                print(f"[agent] Memory analysis error: {e}")
                return "Не вдалося проаналізувати пам'ять комп'ютера."

        if action in ("set_volume", "volume_up", "volume_down", "mute", "unmute"):
            try:
                from tools import system
                function = getattr(system, action)
                return str(function(target)) if target else str(function())
            except Exception as e:
                print(f"[agent] System audio error: {e}")
                return "Не вдалося змінити гучність."

        if action == "shutdown":
            try:
                from tools import system
                return system.shutdown()
            except Exception as e:
                print(f"[agent] Shutdown error: {e}")
                return "Не вдалося вимкнути комп'ютер."

        if action == "restart":
            try:
                from tools import system
                return system.restart()
            except Exception as e:
                print(f"[agent] Restart error: {e}")
                return "Не вдалося перезавантажити комп'ютер."

        if action == "chat":
            return target or "Так, слухаю."

        if action == "stop":
            self.follow_up_active = False
            return "До зустрічі."

        return "Не зовсім зрозумів команду."

    def set_follow_up(self, active: bool):
        self.follow_up_active = bool(active)
        print("[agent] Follow-up режим активовано." if self.follow_up_active else "[agent] Режим wake word.")

    def is_follow_up_active(self):
        return self.follow_up_active

    def get_context(self):
        return self.memory.context()

    def get_last_command(self):
        return self.memory.last_command

    def get_last_result(self):
        return self.memory.last_result

    def get_last_action(self):
        return self.last_action

    def get_last_target(self):
        return self.last_target

    def clear_memory(self):
        self.memory.clear()
        self.follow_up_active = False
        self.last_action = None
        self.last_target = None
        print("[agent] Пам'ять очищено.")


agent = JarvisAgent()


def process(command: str) -> str:
    return agent.process(command)


def set_follow_up(active: bool):
    agent.set_follow_up(active)


def is_follow_up_active():
    return agent.is_follow_up_active()
