"""
JARVIS Agent Core

Центральний шар між jarvis.py та brain.py.

Відповідає за:
- прийом команд;
- пам'ять;
- контекст діалогу;
- швидку обробку простих команд;
- передачу складних команд у brain.py;
- збереження action / target.
"""

from command_router import (
    route,
    get_last_route,
)

from brain import (
    handle,
    get_last_parsed,
)

from .memory import Memory


class JarvisAgent:

    def __init__(self):

        self.memory = Memory()

        self.follow_up_active = False

        self.last_action = None
        self.last_target = None

    def process(
        self,
        command: str
    ) -> str:

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
                    target=""
                )

                return response

            # =================================================
            # LOCAL ROUTER
            # =================================================

            local_response = route(command)

            if local_response is not None:

                print(
                    "[agent] Виконано локально."
                )

                response = str(
                    local_response
                ).strip()

                action, target = get_last_route()

            # =================================================
            # BRAIN
            # =================================================

            else:

                context = self.memory.context()

                print(
                    f"[agent] Контекст: {context}"
                )

                response = handle(
                    command,
                    context=context
                )

                if response is None:
                    response = ""

                response = str(
                    response
                ).strip()

                action, target = get_last_parsed()

            # =================================================
            # SAVE ACTION / TARGET
            # =================================================

            self.last_action = action
            self.last_target = target

            # =================================================
            # MEMORY
            # =================================================

            self.memory.remember(
                command,
                response,
                action=action,
                target=target
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
                target=""
            )

            return response

    # ========================================================
    # FOLLOW-UP
    # ========================================================

    def set_follow_up(
        self,
        active: bool
    ):

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