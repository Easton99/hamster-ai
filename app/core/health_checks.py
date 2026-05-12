from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.app_context import AppContext

OK      = "ok"
WARNING = "warning"
FAIL    = "fail"


@dataclass
class HealthResult:
    name: str
    status: str        # OK | WARNING | FAIL
    message: str
    fix_key: str = ""  # non-empty when a self-fix is available


def check_ollama(app: "AppContext") -> HealthResult:
    try:
        from app.llm.ollama_client import OllamaClient
        client = OllamaClient(
            base_url=app.settings.get("ollama_url", "http://localhost:11434"),
            model=app.settings.get("model", "llama3.2:3b"),
        )
        if client.is_available():
            return HealthResult("Ollama", OK, "Running.")
        return HealthResult("Ollama", FAIL, "Not reachable. Is Ollama running?", fix_key="start_ollama")
    except Exception as exc:
        return HealthResult("Ollama", FAIL, f"Error: {exc}", fix_key="start_ollama")


def check_model(app: "AppContext") -> HealthResult:
    model = app.settings.get("model", "llama3.2:3b")
    try:
        from app.llm.ollama_client import OllamaClient, OllamaError
        client = OllamaClient(
            base_url=app.settings.get("ollama_url", "http://localhost:11434"),
            model=model,
        )
        if not client.is_available():
            return HealthResult("Model", WARNING, "Ollama not running — cannot check.", fix_key="start_ollama")
        models = client.list_models()
        if model in models:
            return HealthResult("Model", OK, f"{model} is installed.")
        return HealthResult("Model", FAIL, f"{model} not found. Pull it first.", fix_key="pull_model")
    except Exception as exc:
        return HealthResult("Model", WARNING, f"Could not check: {exc}")


def check_database(app: "AppContext") -> HealthResult:
    try:
        db_path: Path = app.data_dir / "hamster_ai.db"
        if not db_path.exists():
            return HealthResult("Database", FAIL, "DB file missing.", fix_key="recreate_folders")
        with app.db.conn() as con:
            con.execute("SELECT 1").fetchone()
        return HealthResult("Database", OK, "SQLite accessible.")
    except Exception as exc:
        return HealthResult("Database", FAIL, f"DB error: {exc}")


def check_disk_space(app: "AppContext") -> HealthResult:
    try:
        import shutil
        total, used, free = shutil.disk_usage(app.base_dir)
        free_gb = free / (1024 ** 3)
        if free_gb < 0.5:
            return HealthResult("Disk space", FAIL, f"Only {free_gb:.1f} GB free — very low.")
        if free_gb < 2.0:
            return HealthResult("Disk space", WARNING, f"{free_gb:.1f} GB free — getting low.")
        return HealthResult("Disk space", OK, f"{free_gb:.1f} GB free.")
    except Exception as exc:
        return HealthResult("Disk space", WARNING, f"Could not check: {exc}")


def check_config(app: "AppContext") -> HealthResult:
    cfg_path = app.config_dir / "settings.json"
    if not cfg_path.exists():
        return HealthResult("Config", WARNING, "settings.json missing — using defaults.", fix_key="repair_config")
    try:
        import json
        with open(cfg_path, encoding="utf-8") as f:
            json.load(f)
        return HealthResult("Config", OK, "settings.json valid.")
    except Exception as exc:
        return HealthResult("Config", FAIL, f"settings.json corrupt: {exc}", fix_key="repair_config")


def check_log_dir(app: "AppContext") -> HealthResult:
    try:
        app.log_dir.mkdir(parents=True, exist_ok=True)
        test = app.log_dir / ".write_test"
        test.write_text("x")
        test.unlink()
        return HealthResult("Log directory", OK, f"{app.log_dir} writable.")
    except Exception as exc:
        return HealthResult("Log directory", FAIL, f"Cannot write logs: {exc}", fix_key="recreate_folders")


def check_plugins(app: "AppContext") -> HealthResult:
    if app.plugin_manager is None:
        return HealthResult("Plugins", WARNING, "Plugin manager not initialised.")
    loaded = app.plugin_manager.list_plugins()
    return HealthResult("Plugins", OK, f"{len(loaded)} plugin(s) loaded.")


def run_all(app: "AppContext") -> list[HealthResult]:
    checks = [
        check_ollama,
        check_model,
        check_database,
        check_disk_space,
        check_config,
        check_log_dir,
        check_plugins,
    ]
    results = []
    for fn in checks:
        try:
            results.append(fn(app))
        except Exception as exc:
            results.append(HealthResult(fn.__name__, FAIL, f"Unexpected error: {exc}"))
    return results
