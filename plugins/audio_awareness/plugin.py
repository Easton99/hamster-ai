"""Audio Awareness plugin — detects when system audio is playing."""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from app.plugins.plugin_base import PluginBase

if TYPE_CHECKING:
    from app.core.app_context import AppContext

_POLL_INTERVAL = 5.0

# pycaw is optional — degrade gracefully if not installed
try:
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation  # type: ignore
    from comtypes import CLSCTX_ALL  # type: ignore
    _PYCAW_OK = True
except Exception:
    _PYCAW_OK = False


def _audio_playing() -> bool:
    """Return True if any audio session has a non-zero peak level."""
    if not _PYCAW_OK:
        return False
    try:
        for session in AudioUtilities.GetAllSessions():
            try:
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                if meter.GetPeakValue() > 0.01:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _audio_app() -> str:
    """Return the name of the first process with audio playing, or ''."""
    if not _PYCAW_OK:
        return ""
    try:
        for session in AudioUtilities.GetAllSessions():
            try:
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                if meter.GetPeakValue() > 0.01 and session.Process:
                    return session.Process.name()
            except Exception:
                continue
    except Exception:
        pass
    return ""


class Plugin(PluginBase):
    name = "audio_awareness"
    description = "Detects when system audio is playing and which app is producing it"
    enabled_by_default = True
    dependencies = []
    permissions_required = []

    def on_start(self, app: "AppContext") -> None:
        self._app = app
        self._playing = False
        self._stop = threading.Event()

        if not _PYCAW_OK:
            app.logger.info(
                "audio_awareness: pycaw not installed — audio detection disabled. "
                "Run: pip install pycaw"
            )

        self._thread = threading.Thread(
            target=self._run, daemon=True, name="AudioAwareness"
        )
        self._thread.start()

    def on_stop(self, app: "AppContext") -> None:
        self._stop.set()

    def on_event(self, event: str, data) -> None:
        pass

    def get_commands(self) -> dict:
        return {"/audio": self._cmd_audio}

    def is_playing(self) -> bool:
        return self._playing

    # ── Background poll ───────────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop.wait(_POLL_INTERVAL):
            try:
                self._tick()
            except Exception:
                pass

    def _tick(self) -> None:
        now_playing = _audio_playing()
        if now_playing and not self._playing:
            self._playing = True
            self._app.event_bus.emit("audio_started", {"app": _audio_app()})
        elif not now_playing and self._playing:
            self._playing = False
            self._app.event_bus.emit("audio_stopped", {})

    # ── Commands ──────────────────────────────────────────────────────────────

    def _cmd_audio(self, app: "AppContext", args: str) -> str:
        if not _PYCAW_OK:
            return "Audio detection unavailable — install pycaw: pip install pycaw"
        if self._playing:
            app_name = _audio_app()
            return f"Audio is playing ({app_name})." if app_name else "Audio is playing."
        return "No audio playing."
