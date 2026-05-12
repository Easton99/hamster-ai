import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.app_context import AppContext

# Work Mode: Omnissa Horizon Client and related processes
_WORK_PATTERNS: frozenset[str] = frozenset([
    "horizon", "vmware-view", "omnissa", "vmware horizon",
])

# Game executables — only present when the game is actually running.
# Anti-cheat services (vgc.exe, vgtray.exe, BEService.exe) are intentionally
# excluded because they run as Windows services even when no game is open.
_GAME_EXECUTABLES: frozenset[str] = frozenset([
    "valorant.exe",
    "fortniteclient-win64-shipping.exe",
    "cod.exe",
    "r5apex.exe",
    "cs2.exe",
    "rocketleague.exe",
    "overwatch.exe",
    "overwatch2.exe",
    "destiny2.exe",
    "pubg.exe",
    "eldenring.exe",
])

_POLL_INTERVAL = 8.0  # seconds


class ProcessMonitor:
    def __init__(self, app: "AppContext") -> None:
        self._app = app
        self._log = logging.getLogger("hamster_ai.process_monitor")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        try:
            import psutil  # noqa: F401
        except ImportError:
            self._log.warning("psutil not installed — process monitoring disabled. Run: pip install psutil")
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="ProcessMonitor")
        self._thread.start()
        self._log.info("Process monitor started.")

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        import psutil

        while not self._stop.wait(_POLL_INTERVAL):
            try:
                self._check(psutil)
            except Exception as exc:
                self._log.debug(f"Process monitor poll error: {exc}")

    def _check(self, psutil) -> None:
        from app.observer.active_window import get_active_window

        modes = self._app.modes
        work_detected = False
        game_detected = False

        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info["name"] or "").lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            if any(p in name for p in _WORK_PATTERNS):
                work_detected = True

            if name in _GAME_EXECUTABLES:
                game_detected = True

            if work_detected and game_detected:
                break

        # Also check active window title (spec: detect from process OR title)
        if not work_detected:
            _, title = get_active_window()
            if title and any(p in title.lower() for p in _WORK_PATTERNS):
                work_detected = True

        if self._app.settings.get("work_mode_auto_detect", True):
            if work_detected:
                modes.enable_work_mode()
            else:
                modes.disable_work_mode()

        if self._app.settings.get("game_safe_mode_auto_detect", True):
            if game_detected:
                modes.enable_game_safe_mode()
            else:
                modes.disable_game_safe_mode()
