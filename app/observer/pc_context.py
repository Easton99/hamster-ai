from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.app_context import AppContext

_log = logging.getLogger("hamster_ai.pc_context")
_POLL_INTERVAL = 5.0


@dataclass
class PCSnapshot:
    active_process: str = ""
    active_title: str = ""
    idle_seconds: int = 0
    cpu_percent: float = -1.0
    ram_percent: float = -1.0
    is_fullscreen: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    def to_context_string(self) -> str:
        """Format metadata for injection into the LLM system prompt.

        Follows the spec wording rule: describe what app is active,
        never claim to see screen contents.
        """
        lines: list[str] = []

        if self.active_process:
            lines.append(f"Active app: {self.active_process}")
            if self.active_title and self.active_title.lower() != self.active_process.lower():
                lines.append(f"Window title: {self.active_title}")

        if self.is_fullscreen:
            lines.append("A fullscreen window is active.")

        if self.idle_seconds >= 300:
            lines.append(f"User has been idle for ~{self.idle_seconds // 60} minutes.")
        elif self.idle_seconds >= 60:
            lines.append(f"User has been idle for ~{self.idle_seconds // 60} min.")

        if self.cpu_percent >= 0:
            lines.append(f"CPU: {self.cpu_percent:.0f}%  RAM: {self.ram_percent:.0f}%")

        if not lines:
            return ""

        return "PC context:\n" + "\n".join(f"  {ln}" for ln in lines)


class PCContextCollector:
    """Polls PC metadata on a background thread and exposes the latest snapshot.

    Also auto-detects Private Mode from protected apps/titles, respecting
    whether the mode was toggled manually vs automatically.
    """

    def __init__(self, app: "AppContext") -> None:
        self._app = app
        self._lock = threading.Lock()
        self._snapshot = PCSnapshot()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._auto_private_active = False

    def start(self) -> None:
        # Prime psutil CPU measurement — first call always returns 0.0
        try:
            import psutil
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

        self._thread = threading.Thread(
            target=self._run, daemon=True, name="PCContextCollector"
        )
        self._thread.start()
        _log.info("PC context collector started.")

    def stop(self) -> None:
        self._stop.set()

    def get_snapshot(self) -> PCSnapshot:
        with self._lock:
            return self._snapshot

    def _run(self) -> None:
        while not self._stop.wait(_POLL_INTERVAL):
            try:
                self._collect()
            except Exception as exc:
                _log.debug(f"PC context poll error: {exc}")

    def _collect(self) -> None:
        from app.observer.active_window import get_active_window
        from app.observer.fullscreen import is_fullscreen
        from app.observer.idle import get_idle_seconds
        from app.observer.system_usage import get_cpu_percent, get_ram_percent

        process, title = get_active_window()
        idle = get_idle_seconds()
        cpu = get_cpu_percent()
        ram = get_ram_percent()
        fullscreen = is_fullscreen()

        snap = PCSnapshot(
            active_process=process,
            active_title=title,
            idle_seconds=idle,
            cpu_percent=cpu,
            ram_percent=ram,
            is_fullscreen=fullscreen,
        )

        with self._lock:
            self._snapshot = snap

        self._check_private_mode(process, title)

    def _check_private_mode(self, process: str, title: str) -> None:
        if not self._app.settings.get("private_mode_auto_detect", True):
            return

        modes = self._app.modes
        if modes is None:
            return

        from app.observer.protected_apps import is_protected

        if is_protected(process, title):
            if not modes.private_mode:
                _log.info("Auto-enabling Private Mode: protected app/title detected.")
                modes.enable_private_mode()
                self._auto_private_active = True
        else:
            # Only auto-disable if we were the ones who enabled it
            if self._auto_private_active and modes.private_mode:
                modes.disable_private_mode()
                self._auto_private_active = False
