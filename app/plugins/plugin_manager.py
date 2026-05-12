import importlib.util
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.event_bus import (
    ACTIVE_WINDOW_CHANGED,
    APP_EXITING,
    APP_STARTED,
    ASSISTANT_MESSAGE,
    AUDIO_STARTED,
    AUDIO_STOPPED,
    COMMAND_RECEIVED,
    DAY_ENDED,
    ERROR_LOGGED,
    FOCUS_MODE_DISABLED,
    FOCUS_MODE_ENABLED,
    GAME_SAFE_MODE_DISABLED,
    GAME_SAFE_MODE_ENABLED,
    HEALTH_CHECK_COMPLETED,
    NOTIFY,
    PLUGIN_DISABLED,
    PLUGIN_ENABLED,
    PRIVATE_MODE_DISABLED,
    PRIVATE_MODE_ENABLED,
    SESSION_ENDED,
    SESSION_STARTED,
    SYSTEM_IDLE,
    USER_MESSAGE,
    WEEK_ENDED,
    WORK_MODE_DISABLED,
    WORK_MODE_ENABLED,
)
from app.plugins.plugin_base import PluginBase

if TYPE_CHECKING:
    from app.core.app_context import AppContext

_ALL_EVENTS = [
    APP_STARTED, APP_EXITING, USER_MESSAGE, ASSISTANT_MESSAGE, COMMAND_RECEIVED,
    ACTIVE_WINDOW_CHANGED, SYSTEM_IDLE, SESSION_STARTED, SESSION_ENDED,
    DAY_ENDED, WEEK_ENDED, WORK_MODE_ENABLED, WORK_MODE_DISABLED,
    PRIVATE_MODE_ENABLED, PRIVATE_MODE_DISABLED, FOCUS_MODE_ENABLED,
    FOCUS_MODE_DISABLED, GAME_SAFE_MODE_ENABLED, GAME_SAFE_MODE_DISABLED,
    PLUGIN_ENABLED, PLUGIN_DISABLED, ERROR_LOGGED, HEALTH_CHECK_COMPLETED,
    NOTIFY, AUDIO_STARTED, AUDIO_STOPPED,
]


class PluginManager:
    def __init__(self, app: "AppContext") -> None:
        self._app = app
        self._plugins: dict[str, PluginBase] = {}
        self._active: set[str] = set()
        self._handlers: dict[str, Any] = {}           # name -> event handler fn
        self._plugin_cmds: dict[str, list[str]] = {}  # name -> registered command keys
        self._log = logging.getLogger("hamster_ai.plugins")

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_plugins(self) -> None:
        plugins_dir = self._app.plugins_dir
        if not plugins_dir.exists():
            self._log.info("No plugins/ directory found — skipping plugin load.")
            return

        # None means first run (no saved state yet) — fall back to enabled_by_default.
        # A list (even empty) means the user has explicitly saved their preferences.
        saved = self._app.settings.get("plugins_enabled")
        has_saved_state = saved is not None
        enabled_set: set[str] = set(saved) if has_saved_state else set()

        for plugin_dir in sorted(plugins_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            plugin_file = plugin_dir / "plugin.py"
            if not plugin_file.exists():
                continue
            self._load_one(plugin_file, enabled_set=enabled_set, has_saved_state=has_saved_state)

    def _load_one(self, plugin_file: Path, enabled_set: set, has_saved_state: bool) -> None:
        plugin_name = plugin_file.parent.name
        try:
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_name}", plugin_file
            )
            module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(module)  # type: ignore[union-attr]

            plugin_class = getattr(module, "Plugin", None)
            if plugin_class is None or not (
                isinstance(plugin_class, type) and issubclass(plugin_class, PluginBase)
            ):
                self._log.warning(f"Plugin '{plugin_name}' has no valid Plugin class — skipped.")
                return

            instance: PluginBase = plugin_class()
            self._plugins[plugin_name] = instance
            self._log.info(f"Loaded plugin: {plugin_name}")

            should_enable = (
                plugin_name in enabled_set if has_saved_state else instance.enabled_by_default
            )
            if should_enable:
                self.enable_plugin(plugin_name)

        except Exception:
            self._log.error(f"Failed to load plugin '{plugin_name}'", exc_info=True)

    # ── Enable / Disable ─────────────────────────────────────────────────────

    def enable_plugin(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin is None:
            self._log.warning(f"Cannot enable unknown plugin: {name}")
            return False
        if name in self._active:
            return True

        try:
            plugin.on_start(self._app)
        except Exception:
            self._log.error(f"Plugin '{name}' raised during on_start", exc_info=True)
            return False

        self._active.add(name)

        # Per-plugin event handler — catches exceptions so crashes are isolated
        def _handler(event: str, data: Any, p: PluginBase = plugin, n: str = name) -> None:
            try:
                p.on_event(event, data)
            except Exception:
                self._log.error(f"Plugin '{n}' raised in on_event({event})", exc_info=True)

        self._handlers[name] = _handler
        for ev in _ALL_EVENTS:
            self._app.event_bus.subscribe(ev, _handler)

        # Register plugin commands with the dispatcher
        try:
            cmds = plugin.get_commands() or {}
        except Exception:
            self._log.error(f"Plugin '{name}' raised in get_commands()", exc_info=True)
            cmds = {}

        registered: list[str] = []
        if self._app.commands and cmds:
            for cmd_name, handler_or_pair in cmds.items():
                if isinstance(handler_or_pair, tuple) and len(handler_or_pair) == 2:
                    handler, desc = handler_or_pair
                else:
                    handler, desc = handler_or_pair, f"[plugin: {name}]"
                self._app.commands.register(cmd_name, handler, desc or f"[plugin: {name}]")
                registered.append(cmd_name.lstrip("/").lower())
        self._plugin_cmds[name] = registered

        self._log.info(f"Plugin enabled: {name}")
        self._app.event_bus.emit(PLUGIN_ENABLED, {"plugin": name})
        self._save_enabled_state()
        return True

    def disable_plugin(self, name: str, _save: bool = True) -> bool:
        plugin = self._plugins.get(name)
        if plugin is None or name not in self._active:
            return False

        try:
            plugin.on_stop(self._app)
        except Exception:
            self._log.error(f"Plugin '{name}' raised during on_stop", exc_info=True)

        # Unsubscribe from all events
        handler = self._handlers.pop(name, None)
        if handler:
            for ev in _ALL_EVENTS:
                self._app.event_bus.unsubscribe(ev, handler)

        # Unregister plugin commands
        if self._app.commands:
            for cmd in self._plugin_cmds.pop(name, []):
                self._app.commands.unregister(cmd)

        self._active.discard(name)
        self._log.info(f"Plugin disabled: {name}")
        self._app.event_bus.emit(PLUGIN_DISABLED, {"plugin": name})
        if _save:
            self._save_enabled_state()
        return True

    def stop_all(self) -> None:
        for name in list(self._active):
            self.disable_plugin(name, _save=False)

    def _save_enabled_state(self) -> None:
        self._app.settings.set("plugins_enabled", list(self._active))

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_plugin(self, name: str) -> PluginBase | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "description": p.description,
                "enabled": name in self._active,
                "enabled_by_default": p.enabled_by_default,
            }
            for name, p in self._plugins.items()
        ]
