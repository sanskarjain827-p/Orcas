from collections import deque


class SessionMemory:
    \"\"\"
    Keeps the current conversation history in memory.
    Automatically trims to max_turns to avoid blowing
    the context window.
    \"\"\"

    def __init__(self, max_turns: int = 40):
        self.max_turns = max_turns
        self._history  = deque(maxlen=max_turns * 2)  # *2 for user+assistant pairs
        self.active_agent: str = "orcas"

    def add(self, role: str, content: str):
        self._history.append({"role": role, "content": content})

    def get(self) -> list:
        return list(self._history)

    def clear(self):
        self._history.clear()
        self.active_agent = "orcas"

    def summary(self) -> str:
        turns = len(self._history) // 2
        return f"{turns} turns in session | active agent: {self.active_agent}"
