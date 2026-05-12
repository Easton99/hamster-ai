import threading
from collections import defaultdict
from typing import Any, Callable

# ── Event name constants ─────────────────────────────────────────────────────
APP_STARTED = "app_started"
APP_EXITING = "app_exiting"
USER_MESSAGE = "user_message"
ASSISTANT_MESSAGE = "assistant_message"
COMMAND_RECEIVED = "command_received"
ACTIVE_WINDOW_CHANGED = "active_window_changed"
SYSTEM_IDLE = "system_idle"
SESSION_STARTED = "session_started"
SESSION_ENDED = "session_ended"
DAY_ENDED = "day_ended"
WEEK_ENDED = "week_ended"
WORK_MODE_ENABLED = "work_mode_enabled"
WORK_MODE_DISABLED = "work_mode_disabled"
PRIVATE_MODE_ENABLED = "private_mode_enabled"
PRIVATE_MODE_DISABLED = "private_mode_disabled"
FOCUS_MODE_ENABLED = "focus_mode_enabled"
FOCUS_MODE_DISABLED = "focus_mode_disabled"
GAME_SAFE_MODE_ENABLED = "game_safe_mode_enabled"
GAME_SAFE_MODE_DISABLED = "game_safe_mode_disabled"
PLUGIN_ENABLED = "plugin_enabled"
PLUGIN_DISABLED = "plugin_disabled"
ERROR_LOGGED = "error_logged"
HEALTH_CHECK_COMPLETED = "health_check_completed"
NOTIFY = "notify"
MINI_POPUP = "mini_popup"
AUDIO_STARTED = "audio_started"
AUDIO_STOPPED = "audio_stopped"


class EventBus:
    """Thread-safe pub/sub event bus. Errors in one handler do not affect others."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event: str, callback: Callable) -> None:
        with self._lock:
            self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> None:
        with self._lock:
            self._subscribers[event] = [
                cb for cb in self._subscribers[event] if cb is not callback
            ]

    def emit(self, event: str, data: Any = None) -> None:
        with self._lock:
            callbacks = list(self._subscribers[event])
        for callback in callbacks:
            try:
                callback(event, data)
            except Exception as exc:
                # Avoid recursive loop if error_logged itself fails
                print(f"[EventBus] Handler error for '{event}': {exc}")
