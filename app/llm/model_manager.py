from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.ollama_client import OllamaClient


class ModelManager:
    def __init__(self, client: "OllamaClient") -> None:
        self._client = client

    def list_available(self) -> list[str]:
        try:
            return self._client.list_models()
        except Exception:
            return []

    def switch(self, model_name: str) -> None:
        self._client.model = model_name

    def current(self) -> str:
        return self._client.model
