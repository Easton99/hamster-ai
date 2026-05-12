import json
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "model": "llama3.2:3b",
    "ollama_url": "http://localhost:11434",
    "personality": "Hamster",
    "start_with_windows": False,
    "greet_on_startup": True,
    "startup_delay_seconds": 30,
    "work_mode_auto_detect": True,
    "private_mode_auto_detect": True,
    "game_safe_mode_auto_detect": True,
    "voice_enabled": False,
    "log_level": "INFO",
    "web_search_enabled": False,
}


class Settings:
    def __init__(self, config_path: Path) -> None:
        self._path = config_path
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        for key, value in DEFAULT_SETTINGS.items():
            if key not in self._data:
                self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def all(self) -> dict[str, Any]:
        return dict(self._data)
