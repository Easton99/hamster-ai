import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.health_checks import HealthResult

if TYPE_CHECKING:
    from app.core.app_context import AppContext


@dataclass
class FixSuggestion:
    key: str
    label: str
    description: str


_FIXES: dict[str, FixSuggestion] = {
    "start_ollama": FixSuggestion(
        key="start_ollama",
        label="Start Ollama",
        description="Run 'ollama serve' to start the local Ollama server.",
    ),
    "pull_model": FixSuggestion(
        key="pull_model",
        label="Pull missing model",
        description="Download the configured model from Ollama.",
    ),
    "recreate_folders": FixSuggestion(
        key="recreate_folders",
        label="Recreate missing folders",
        description="Create any missing data/logs/config directories.",
    ),
    "repair_config": FixSuggestion(
        key="repair_config",
        label="Repair config file",
        description="Rewrite settings.json with default values.",
    ),
    "clear_logs": FixSuggestion(
        key="clear_logs",
        label="Clear old log files",
        description="Delete rotated log files to free space.",
    ),
}


class SelfFix:
    def __init__(self, app: "AppContext") -> None:
        self._app = app

    def suggestions_for(self, results: list[HealthResult]) -> list[FixSuggestion]:
        seen: set[str] = set()
        out: list[FixSuggestion] = []
        for r in results:
            if r.fix_key and r.fix_key in _FIXES and r.fix_key not in seen:
                out.append(_FIXES[r.fix_key])
                seen.add(r.fix_key)
        return out

    def apply(self, fix_key: str) -> tuple[bool, str]:
        """Apply a safe fix. Returns (success, message)."""
        app = self._app
        try:
            if fix_key == "start_ollama":
                return self._start_ollama()
            if fix_key == "pull_model":
                return self._pull_model()
            if fix_key == "recreate_folders":
                return self._recreate_folders()
            if fix_key == "repair_config":
                return self._repair_config()
            if fix_key == "clear_logs":
                return self._clear_logs()
            return False, f"Unknown fix key: {fix_key}"
        except Exception as exc:
            app.logger.error(f"Self-fix '{fix_key}' failed: {exc}", exc_info=True)
            return False, str(exc)

    def _start_ollama(self) -> tuple[bool, str]:
        import shutil
        ollama = shutil.which("ollama")
        if ollama is None:
            # Try the default install path on Windows
            from pathlib import Path
            import os
            candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
            if candidate.exists():
                ollama = str(candidate)
        if ollama is None:
            return False, "ollama executable not found. Install Ollama from https://ollama.com"
        subprocess.Popen([ollama, "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
        return True, "Ollama server starting. Give it a few seconds."

    def _pull_model(self) -> tuple[bool, str]:
        import shutil, os
        from pathlib import Path
        model = self._app.settings.get("model", "llama3.2:3b")
        ollama = shutil.which("ollama")
        if ollama is None:
            candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
            if candidate.exists():
                ollama = str(candidate)
        if ollama is None:
            return False, "ollama executable not found."
        subprocess.Popen([ollama, "pull", model], creationflags=subprocess.CREATE_NO_WINDOW)
        return True, f"Pulling {model} in the background. This may take a few minutes."

    def _recreate_folders(self) -> tuple[bool, str]:
        app = self._app
        for d in (app.data_dir, app.config_dir, app.log_dir, app.plugins_dir):
            d.mkdir(parents=True, exist_ok=True)
        return True, "Missing folders recreated."

    def _repair_config(self) -> tuple[bool, str]:
        from app.core.settings import DEFAULT_SETTINGS
        import json
        cfg = self._app.config_dir / "settings.json"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)
        return True, "settings.json rewritten with defaults."

    def _clear_logs(self) -> tuple[bool, str]:
        removed = 0
        for f in self._app.log_dir.glob("hamster_ai.log.*"):
            f.unlink(missing_ok=True)
            removed += 1
        return True, f"Cleared {removed} rotated log file(s)."
