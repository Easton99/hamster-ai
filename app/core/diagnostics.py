import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.health_checks import HealthResult, run_all
from app.core.self_fix import FixSuggestion, SelfFix

if TYPE_CHECKING:
    from app.core.app_context import AppContext

_REDACT = ("password", "token", "secret")


class Diagnostics:
    def __init__(self, app: "AppContext") -> None:
        self._app = app
        self._self_fix = SelfFix(app)

    def run_checks(self) -> list[HealthResult]:
        results = run_all(self._app)
        self._app.event_bus.emit("health_check_completed", {"results": len(results)})
        return results

    def suggestions_for(self, results: list[HealthResult]) -> list[FixSuggestion]:
        return self._self_fix.suggestions_for(results)

    def apply_fix(self, fix_key: str) -> tuple[bool, str]:
        ok, msg = self._self_fix.apply(fix_key)
        level = "info" if ok else "error"
        getattr(self._app.logger, level)(f"Self-fix '{fix_key}': {msg}")
        return ok, msg

    def recent_errors(self, n: int = 30) -> list[str]:
        current, older = self.recent_errors_split(n)
        return current + older

    def recent_errors_split(self, n: int = 30) -> tuple[list[str], list[str]]:
        """Return (current_session_lines, older_lines) filtered to warnings/errors."""
        log_file = self._app.log_dir / "hamster_ai.log"
        if not log_file.exists():
            return [], []
        current: list[str] = []
        older: list[str] = []
        session_start = self._app.session_started
        try:
            with open(log_file, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "| ERROR" not in line and "| CRITICAL" not in line and "| WARNING" not in line:
                        continue
                    stripped = line.rstrip()
                    ts = _parse_log_ts(stripped)
                    if ts is not None and ts >= session_start.replace(microsecond=0):
                        current.append(stripped)
                    else:
                        older.append(stripped)
        except OSError:
            pass
        return current[-n:], older[-n:]


def _parse_log_ts(line: str) -> "datetime | None":
    from datetime import datetime
    try:
        return datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    def all_recent_logs(self, n: int = 100) -> list[str]:
        log_file = self._app.log_dir / "hamster_ai.log"
        if not log_file.exists():
            return []
        try:
            with open(log_file, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return [l.rstrip() for l in lines[-n:]]
        except OSError:
            return []

    def clear_logs(self) -> None:
        log_file = self._app.log_dir / "hamster_ai.log"
        if log_file.exists():
            log_file.write_text("", encoding="utf-8")
        for old in self._app.log_dir.glob("hamster_ai.log.*"):
            old.unlink(missing_ok=True)
        self._app.logger.info("Logs cleared by user.")

    def export_bundle(self, dest_dir: Path | None = None) -> Path:
        dest_dir = dest_dir or self._app.data_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_path = dest_dir / f"hamster_diagnostics_{ts}.zip"

        results = self.run_checks()

        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Log file
            log_file = self._app.log_dir / "hamster_ai.log"
            if log_file.exists():
                zf.write(log_file, "hamster_ai.log")

            # Redacted settings
            settings = self._app.settings.all()
            redacted = {
                k: "[REDACTED]" if any(t in k.lower() for t in _REDACT) else v
                for k, v in settings.items()
            }
            zf.writestr("settings_redacted.json", json.dumps(redacted, indent=2))

            # Health check summary
            summary_lines = [f"{r.name}: {r.status.upper()} — {r.message}" for r in results]
            zf.writestr("health_checks.txt", "\n".join(summary_lines))

        self._app.logger.info(f"Diagnostic bundle exported: {bundle_path}")
        return bundle_path
