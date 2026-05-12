"""Voice Output plugin — speaks assistant replies using local TTS (pyttsx3 / Windows SAPI)."""
from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING

from app.plugins.plugin_base import PluginBase

if TYPE_CHECKING:
    from app.core.app_context import AppContext

try:
    import pyttsx3
    _PYTTSX3_OK = True
except Exception:
    _PYTTSX3_OK = False

_NOT_INSTALLED = (
    "Voice output unavailable — install pyttsx3: pip install pyttsx3"
)


class Plugin(PluginBase):
    name = "voice_output"
    description = "Speaks assistant replies using local TTS (Windows SAPI via pyttsx3)"
    enabled_by_default = False
    dependencies = []
    permissions_required = []

    def on_start(self, app: "AppContext") -> None:
        self._app = app
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._ready = False
        self._stop_evt = threading.Event()

        if not _PYTTSX3_OK:
            app.logger.info(
                "voice_output: pyttsx3 not installed — TTS disabled. "
                "Run: pip install pyttsx3"
            )
            return

        self._thread = threading.Thread(
            target=self._run, daemon=True, name="VoiceOutput"
        )
        self._thread.start()

        app.event_bus.subscribe("assistant_message", self._on_assistant_message)

    def on_stop(self, app: "AppContext") -> None:
        self._stop_evt.set()
        self._queue.put(None)
        app.event_bus.unsubscribe("assistant_message", self._on_assistant_message)

    def on_event(self, event: str, data) -> None:
        pass

    def get_commands(self) -> dict:
        return {
            "/voice":      self._cmd_voice,
            "/voice-test": self._cmd_voice_test,
        }

    # ── Event handler ──────────────────────────────────────────────────────────

    def _on_assistant_message(self, event: str, data) -> None:
        if not self._ready:
            return

        modes = self._app.modes
        if modes and (modes.work_mode or modes.private_mode or modes.game_safe_mode):
            return
        if modes and modes.focus_mode:
            if not self._app.settings.get("voice_speak_in_focus", False):
                return

        if not self._app.settings.get("voice_enabled", True):
            return
        if not self._app.settings.get("speak_chat_replies", True):
            return

        text = data.get("text", "") if isinstance(data, dict) else str(data)
        if text.strip():
            self._queue.put(text)

    # ── TTS thread ─────────────────────────────────────────────────────────────

    def _run(self) -> None:
        try:
            engine = pyttsx3.init()
            self._apply_settings(engine)
            self._ready = True
            self._app.logger.info("voice_output: TTS engine ready.")
        except Exception as exc:
            self._app.logger.error(f"voice_output: failed to initialise — {exc}")
            return

        while not self._stop_evt.is_set():
            try:
                text = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None:
                break
            try:
                clean = _strip_markdown(text)
                if len(clean) > 500:
                    clean = clean[:497] + "..."
                engine.say(clean)
                engine.runAndWait()
            except Exception as exc:
                self._app.logger.debug(f"voice_output: TTS error — {exc}")

    def _apply_settings(self, engine) -> None:
        rate = self._app.settings.get("voice_speed", 175)
        volume = self._app.settings.get("voice_volume", 0.9)
        voice_name = self._app.settings.get("voice_name", "")
        engine.setProperty("rate", int(rate))
        engine.setProperty("volume", float(volume))
        if voice_name:
            for v in engine.getProperty("voices"):
                if voice_name.lower() in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break

    # ── Commands ──────────────────────────────────────────────────────────────

    def _cmd_voice(self, app: "AppContext", args: str) -> str:
        if not _PYTTSX3_OK:
            return _NOT_INSTALLED
        arg = args.strip().lower()
        if arg in ("on", "enable"):
            app.settings.set("voice_enabled", True)
            return "Voice output enabled."
        if arg in ("off", "disable"):
            app.settings.set("voice_enabled", False)
            return "Voice output disabled."
        on = app.settings.get("voice_enabled", True)
        status = "on" if on else "off"
        ready = " (engine ready)" if self._ready else " (engine not ready)"
        return f"Voice output is {status}{ready}. Use /voice on or /voice off."

    def _cmd_voice_test(self, app: "AppContext", args: str) -> str:
        if not _PYTTSX3_OK:
            return _NOT_INSTALLED
        if not self._ready:
            return "TTS engine not ready. Enable the plugin and wait a moment."
        self._queue.put("Hamster online. Text to speech is working.")
        return "Speaking test phrase."


# ── Helpers ────────────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    return text.replace("**", "").replace("*", "").replace("`", "").replace("#", "")
