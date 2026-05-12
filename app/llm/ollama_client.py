import json
import urllib.error
import urllib.request
from collections.abc import Generator


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            raise OllamaError(f"Could not list models: {exc}") from exc

    def chat_stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        """Yield response content tokens as they stream from Ollama."""
        payload = json.dumps(
            {"model": self.model, "messages": messages, "stream": True}
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for raw_line in resp:
                    line = raw_line.strip()
                    if not line:
                        continue
                    chunk = json.loads(line.decode())
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done"):
                        break
        except urllib.error.URLError as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Non-streaming convenience wrapper — returns the full response."""
        return "".join(self.chat_stream(messages))
