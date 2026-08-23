"""
JARVIS Agent Memory

Короткочасна пам'ять поточного діалогу.
Зберігає не тільки команди, а й дані, корисні для follow-up дій.
"""

from datetime import datetime


class Memory:

    def __init__(self, limit=30):
        self.messages = []
        self.limit = limit

        self.last_command = None
        self.last_result = None
        self.last_action = None
        self.last_target = None

        # Стан, який може використовувати наступна команда.
        self.state = {}

    def remember(self, command, result=None, action=None, target=None, **extra):
        self.last_command = command
        self.last_result = result
        self.last_action = action
        self.last_target = target

        message = {
            "command": command,
            "result": result,
            "action": action,
            "target": target,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
        message.update(extra)

        self.messages.append(message)
        if len(self.messages) > self.limit:
            self.messages.pop(0)

    def remember_state(self, key, value):
        self.state[key] = value

    def get_state(self, key, default=None):
        return self.state.get(key, default)

    def forget_state(self, key):
        self.state.pop(key, None)

    def context(self, limit=12):
        """Повертає компактний контекст для GPT."""
        return self.messages[-limit:]

    def recent(self, limit=5):
        return self.messages[-limit:]

    def last_message(self):
        return self.messages[-1] if self.messages else None

    def has_memory(self):
        return bool(self.messages)

    def size(self):
        return len(self.messages)

    def clear(self):
        self.messages.clear()
        self.state.clear()
        self.last_command = None
        self.last_result = None
        self.last_action = None
        self.last_target = None
        print("[memory] Пам'ять очищено.")
