from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

class SimpleWindowMemory:
    def __init__(self, k: int = 10):
        self.k = k
        self.messages: list[BaseMessage] = []

    def add_user(self, content: str):
        self.messages.append(HumanMessage(content=content))
        self._trim()

    def add_ai(self, content: str):
        self.messages.append(AIMessage(content=content))
        self._trim()

    def clear(self):
        self.messages = []

    def _trim(self):
        if len(self.messages) > self.k * 2:
            self.messages = self.messages[-self.k * 2:]

    def get_messages(self) -> list[BaseMessage]:
        return self.messages

    def message_count(self) -> int:
        return len(self.messages)

    def turn_count(self) -> int:
        return len(self.messages)
