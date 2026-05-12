import logging
import threading
from typing import TYPE_CHECKING

from app.core.event_bus import (
    FOCUS_MODE_DISABLED,
    FOCUS_MODE_ENABLED,
    GAME_SAFE_MODE_DISABLED,
    GAME_SAFE_MODE_ENABLED,
    PRIVATE_MODE_DISABLED,
    PRIVATE_MODE_ENABLED,
    WORK_MODE_DISABLED,
    WORK_MODE_ENABLED,
)

if TYPE_CHECKING:
    from app.core.app_context import AppContext


class ModeManager:
    """Tracks all protective mode states and emits events on transitions."""

    def __init__(self, app: "AppContext") -> None:
        self._app = app
        self._log = logging.getLogger("hamster_ai.modes")
        self._work = False
        self._private = False
        self._focus = False
        self._game_safe = False
        self._focus_timer: threading.Timer | None = None

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def work_mode(self) -> bool:
        return self._work

    @property
    def private_mode(self) -> bool:
        return self._private

    @property
    def focus_mode(self) -> bool:
        return self._focus

    @property
    def game_safe_mode(self) -> bool:
        return self._game_safe

    def is_fully_paused(self) -> bool:
        """Work, Private, or GameSafe — all block automatic activity."""
        return self._work or self._private or self._game_safe

    def active_modes(self) -> list[str]:
        modes = []
        if self._work:      modes.append("Work")
        if self._private:   modes.append("Private")
        if self._focus:     modes.append("Focus")
        if self._game_safe: modes.append("GameSafe")
        return modes

    # ── Work Mode ─────────────────────────────────────────────────────────────

    def enable_work_mode(self) -> None:
        if self._work:
            return
        self._work = True
        self._log.info("Work Mode enabled.")
        self._app.event_bus.emit(WORK_MODE_ENABLED)

    def disable_work_mode(self) -> None:
        if not self._work:
            return
        self._work = False
        self._log.info("Work Mode disabled.")
        self._app.event_bus.emit(WORK_MODE_DISABLED)

    # ── Private Mode ──────────────────────────────────────────────────────────

    def enable_private_mode(self) -> None:
        if self._private:
            return
        self._private = True
        self._log.info("Private Mode enabled.")
        self._app.event_bus.emit(PRIVATE_MODE_ENABLED)

    def disable_private_mode(self) -> None:
        if not self._private:
            return
        self._private = False
        self._log.info("Private Mode disabled.")
        self._app.event_bus.emit(PRIVATE_MODE_DISABLED)

    # ── Focus Mode ────────────────────────────────────────────────────────────

    def enable_focus_mode(self, minutes: float | None = None) -> None:
        if self._focus_timer:
            self._focus_timer.cancel()
            self._focus_timer = None
        self._focus = True
        label = f"{minutes} min" if minutes else "indefinite"
        self._log.info(f"Focus Mode enabled ({label}).")
        self._app.event_bus.emit(FOCUS_MODE_ENABLED, {"minutes": minutes})
        if minutes:
            self._focus_timer = threading.Timer(minutes * 60, self._focus_expired)
            self._focus_timer.daemon = True
            self._focus_timer.start()

    def disable_focus_mode(self) -> None:
        if self._focus_timer:
            self._focus_timer.cancel()
            self._focus_timer = None
        if not self._focus:
            return
        self._focus = False
        self._log.info("Focus Mode disabled.")
        self._app.event_bus.emit(FOCUS_MODE_DISABLED)

    def _focus_expired(self) -> None:
        self._focus = False
        self._focus_timer = None
        self._log.info("Focus Mode expired.")
        self._app.event_bus.emit(FOCUS_MODE_DISABLED)

    # ── Game Safe Mode ────────────────────────────────────────────────────────

    def enable_game_safe_mode(self) -> None:
        if self._game_safe:
            return
        self._game_safe = True
        self._log.info("Game Safe Mode enabled.")
        self._app.event_bus.emit(GAME_SAFE_MODE_ENABLED)

    def disable_game_safe_mode(self) -> None:
        if not self._game_safe:
            return
        self._game_safe = False
        self._log.info("Game Safe Mode disabled.")
        self._app.event_bus.emit(GAME_SAFE_MODE_DISABLED)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def stop(self) -> None:
        if self._focus_timer:
            self._focus_timer.cancel()
