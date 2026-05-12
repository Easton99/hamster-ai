from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from app.plugins.plugin_base import PluginBase

if TYPE_CHECKING:
    from app.core.app_context import AppContext

_POLL_INTERVAL = 10.0  # seconds

# ── Session classifiers ───────────────────────────────────────────────────────

_CODING_PROCS = frozenset([
    "code.exe", "code - insiders.exe", "pycharm64.exe", "pycharm.exe",
    "idea64.exe", "idea.exe", "clion64.exe", "clion.exe", "webstorm64.exe",
    "webstorm.exe", "rider64.exe", "rider.exe", "datagrip64.exe",
    "sublime_text.exe", "notepad++.exe", "nvim.exe", "vim.exe",
    "windowsterminal.exe", "powershell.exe", "powershell_ise.exe",
    "cmd.exe", "wt.exe", "gitbash.exe", "git-cmd.exe",
])

_CODING_TITLE_KEYWORDS = frozenset([
    "visual studio code", "pycharm", "intellij", "webstorm", "rider",
    "clion", "sublime text", "notepad++", "github", "gitlab",
    "git bash", "terminal", "powershell", "command prompt", "wsl",
])

_GAME_PROCS = frozenset([
    "valorant.exe", "fortniteclient-win64-shipping.exe", "cod.exe",
    "r5apex.exe", "cs2.exe", "rocketleague.exe", "overwatch.exe",
    "overwatch2.exe", "destiny2.exe", "pubg.exe", "eldenring.exe",
    "steam.exe", "epicgameslauncher.exe", "battlenet.exe",
])

_GAME_TITLE_KEYWORDS = frozenset([
    "steam", "epic games", "battle.net",
])

_BROWSER_PROCS = frozenset([
    "chrome.exe", "firefox.exe", "msedge.exe", "brave.exe",
    "opera.exe", "vivaldi.exe", "waterfox.exe",
])

_MEDIA_PROCS = frozenset([
    "vlc.exe", "mpc-hc.exe", "mpc-be.exe", "mpv.exe",
    "spotify.exe", "wmplayer.exe", "groove.exe",
    "netflix.exe", "plex.exe",
])

_MEDIA_TITLE_KEYWORDS = frozenset([
    "youtube", "netflix", "twitch", "hulu", "disney+",
    "prime video", "spotify", "soundcloud",
])

_DB_PROCS = frozenset([
    "ssms.exe", "dbeaver.exe", "datagrip64.exe", "datagrip.exe",
    "tableplus.exe", "mysql workbench.exe", "navicat.exe", "pgadmin4.exe",
    "heidisql.exe", "beekeeper-studio.exe",
])

_DB_TITLE_KEYWORDS = frozenset([
    "sql server", "dbeaver", "datagrip", "mysql workbench",
    "pgadmin", "navicat", "tableplus", "heidisql",
])

_IDLE_THRESHOLD = 300  # 5 minutes


def _classify(process: str, title: str, idle_secs: int, fullscreen: bool) -> str:
    proc = process.lower()
    ttl = title.lower()

    if idle_secs >= _IDLE_THRESHOLD:
        return "idle"
    if proc in _GAME_PROCS or (fullscreen and any(k in ttl for k in _GAME_TITLE_KEYWORDS)):
        return "gaming"
    if proc in _CODING_PROCS or any(k in ttl for k in _CODING_TITLE_KEYWORDS):
        return "coding"
    if proc in _DB_PROCS or any(k in ttl for k in _DB_TITLE_KEYWORDS):
        return "database"
    if proc in _MEDIA_PROCS or any(k in ttl for k in _MEDIA_TITLE_KEYWORDS):
        return "media"
    if proc in _BROWSER_PROCS:
        return "browsing"
    return "unknown"


# ── Plugin ────────────────────────────────────────────────────────────────────

class Plugin(PluginBase):
    name = "session_awareness"
    description = "Tracks what you're doing (coding, gaming, browsing…) and logs sessions"
    enabled_by_default = True
    dependencies = []
    permissions_required = []

    def on_start(self, app: "AppContext") -> None:
        self._app = app
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="SessionAwareness"
        )
        self._thread.start()

    def on_stop(self, app: "AppContext") -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        # End whatever session was active
        try:
            app.store.end_active_session()
        except Exception:
            pass

    def on_event(self, event: str, data) -> None:
        pass

    def get_commands(self) -> dict:
        return {
            "/session":  self._cmd_session,
            "/sessions": self._cmd_sessions,
        }

    # ── Background loop ───────────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop.wait(_POLL_INTERVAL):
            try:
                self._tick()
            except Exception as exc:
                import logging
                logging.getLogger("hamster_ai.session_awareness").debug(
                    f"Session tick error: {exc}"
                )

    def _tick(self) -> None:
        snap = self._app.pc_context.get_snapshot() if self._app.pc_context else None
        if snap:
            process = snap.active_process
            title = snap.active_title
            idle = snap.idle_seconds
            fullscreen = snap.is_fullscreen
        else:
            from app.observer.active_window import get_active_window
            from app.observer.idle import get_idle_seconds
            process, title = get_active_window()
            idle = get_idle_seconds()
            fullscreen = False

        # Ignore the hamster app's own process — it becomes "active" whenever
        # the chat window is focused, which would overwrite real session data.
        if process.lower() in ("python.exe", "pythonw.exe"):
            return

        new_type = _classify(process, title, idle, fullscreen)
        primary_app = process or "unknown"

        active = self._app.store.get_active_session()
        if active is None or active.session_type != new_type:
            self._app.store.start_session(new_type, primary_app)

    # ── Commands ──────────────────────────────────────────────────────────────

    def _cmd_session(self, app: "AppContext", args: str) -> str:
        session = app.store.get_active_session()
        if session is None:
            return "No active session."
        return (
            f"Current session: **{session.session_type}**\n"
            f"App: {session.primary_app}\n"
            f"Started: {session.started_at}"
        )

    def _cmd_sessions(self, app: "AppContext", args: str) -> str:
        limit = 10
        if args.strip().isdigit():
            limit = min(int(args.strip()), 50)
        sessions = app.store.recent_sessions(limit=limit)
        if not sessions:
            return "No sessions recorded yet."
        lines = ["Recent sessions:"]
        for s in sessions:
            ended = s.ended_at or "active"
            lines.append(f"  [{s.started_at[:16]}] {s.session_type} ({s.primary_app}) → {ended[:16] if s.ended_at else 'active'}")
        return "\n".join(lines)
