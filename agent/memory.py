"""
JARVIS Agent Memory

Тимчасова пам'ять поточного запуску JARVIS.
"""

from datetime import datetime


class Memory:

    def __init__(self):

        self.messages = []

        self.last_command = None
        self.last_result = None
        self.last_action = None
        self.last_target = None

    def remember(
        self,
        command,
        result=None,
        action=None,
        target=None,
    ):

        self.last_command = command
        self.last_result = result
        self.last_action = action
        self.last_target = target

        current_time = datetime.now().strftime(
            "%H:%M:%S"
        )

        self.messages.append({
            "command": command,
            "result": result,
            "action": action,
            "target": target,
            "time": current_time,
        })

        if len(self.messages) > 20:
            self.messages.pop(0)

    def context(self):

        return self.messages[-10:]

    def last_message(self):

        if not self.messages:
            return None

        return self.messages[-1]

    def clear(self):

        self.messages.clear()

        self.last_command = None
        self.last_result = None
        self.last_action = None
        self.last_target = None

        print("[memory] Пам'ять очищено.")

    def has_memory(self):

        return bool(self.messages)

    def size(self):

        return len(self.messages)