from datetime import datetime
from pathlib import Path

from app.core.event_bus import APP_EXITING, APP_STARTED, EventBus
from app.core.logging_config import setup_logging
from app.core.settings import Settings


class AppContext:
    """Central app object. Pass this around instead of using globals."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.data_dir = base_dir / "data"
        self.config_dir = self.data_dir / "config"
        self.log_dir = self.data_dir / "logs"
        self.plugins_dir = base_dir / "plugins"

        self.session_started: datetime = datetime.now()
        self.settings = Settings(self.config_dir / "settings.json")
        self.logger = setup_logging(
            log_level=self.settings.get("log_level", "INFO"),
            log_dir=self.log_dir,
        )
        self.event_bus = EventBus()

        # Injected in start()
        self.plugin_manager = None
        self.db = None
        self.store = None
        self.commands = None
        self.modes = None
        self.process_monitor = None
        self.pc_context = None
        self.diagnostics = None
        self.notification_history = None
        self.reminder_scheduler = None
        self.hotkey = None
        self.model_manager = None
        self.pending_mini_responses: list[dict] = []
        self.mini_response_history: list[dict] = []

    def setup_model_manager(self, client) -> None:
        from app.llm.model_manager import ModelManager
        self.model_manager = ModelManager(client)

    def setup_hotkey(self, callback) -> None:
        from app.core.hotkey import GlobalHotkey
        hotkey_str = self.settings.get("global_hotkey", "Ctrl+Shift+H")
        enabled = self.settings.get("global_hotkey_enabled", True)
        if not enabled:
            return
        self.hotkey = GlobalHotkey()
        ok = self.hotkey.register(hotkey_str, callback)
        if not ok:
            self.logger.warning(f"Could not register global hotkey: {hotkey_str}")

    def start(self) -> None:
        from app.core.commands import build_dispatcher
        from app.core.diagnostics import Diagnostics
        from app.core.modes import ModeManager
        from app.memory.db import Database
        from app.memory.store import MemoryStore
        from app.observer.pc_context import PCContextCollector
        from app.observer.process_monitor import ProcessMonitor
        from app.plugins.plugin_manager import PluginManager

        self.db = Database(self.data_dir / "hamster_ai.db")
        self.store = MemoryStore(self.db)
        self.modes = ModeManager(self)
        self.diagnostics = Diagnostics(self)
        self.commands = build_dispatcher()

        from app.core.notification_history import NotificationHistory
        from app.core.reminder_scheduler import ReminderScheduler
        self.notification_history = NotificationHistory(self.db)
        self.reminder_scheduler = ReminderScheduler(
            self.db, self._on_reminder_fire
        )
        self.reminder_scheduler.start()

        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_plugins()

        self.process_monitor = ProcessMonitor(self)
        self.process_monitor.start()

        self.pc_context = PCContextCollector(self)
        self.pc_context.start()

        self.logger.info("Hamster AI started.")
        self.event_bus.emit(APP_STARTED)

    def _on_reminder_fire(self, reminder) -> None:
        if self.modes and (self.modes.work_mode or self.modes.private_mode):
            return
        msg = reminder.content
        self.event_bus.emit("notify", {"title": "Reminder", "body": msg})
        self.event_bus.emit("mini_popup", {"title": "Reminder", "body": msg})
        if self.notification_history:
            self.notification_history.add("reminder", msg)

    def stop(self) -> None:
        self.logger.info("Hamster AI stopping.")
        self.event_bus.emit(APP_EXITING)
        if self.pc_context:
            self.pc_context.stop()
        if self.process_monitor:
            self.process_monitor.stop()
        if self.modes:
            self.modes.stop()
        if self.reminder_scheduler:
            self.reminder_scheduler.stop()
        if self.hotkey:
            self.hotkey.unregister()
        if self.plugin_manager:
            self.plugin_manager.stop_all()
