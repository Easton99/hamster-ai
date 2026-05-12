from PySide6.QtCore import QThread, Signal

from app.llm.ollama_client import OllamaClient, OllamaError


class LLMWorker(QThread):
    chunk_received = Signal(str)
    response_done = Signal(str)
    request_error = Signal(str)

    def __init__(self, client: OllamaClient, messages: list[dict]) -> None:
        super().__init__()
        self._client = client
        self._messages = messages
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        parts: list[str] = []
        try:
            for chunk in self._client.chat_stream(self._messages):
                if self._cancelled:
                    return
                self.chunk_received.emit(chunk)
                parts.append(chunk)
            self.response_done.emit("".join(parts))
        except OllamaError as exc:
            self.request_error.emit(str(exc))
