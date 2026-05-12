from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app.core.event_bus import (
    FOCUS_MODE_DISABLED,
    FOCUS_MODE_ENABLED,
    GAME_SAFE_MODE_DISABLED,
    GAME_SAFE_MODE_ENABLED,
    NOTIFY,
    PRIVATE_MODE_DISABLED,
    PRIVATE_MODE_ENABLED,
    WORK_MODE_DISABLED,
    WORK_MODE_ENABLED,
)
from app.desktop.icons import make_hamster_icon

if TYPE_CHECKING:
    from app.core.app_context import AppContext
    from app.llm.ollama_client import OllamaClient
    from app.llm.prompt_builder import PromptBuilder


_ICON_NORMAL = None
_ICON_PAUSED = None


def _normal_icon() -> QIcon:
    global _ICON_NORMAL
    if _ICON_NORMAL is None:
        _ICON_NORMAL = make_hamster_icon(greyed=False)
    return _ICON_NORMAL


def _paused_icon() -> QIcon:
    global _ICON_PAUSED
    if _ICON_PAUSED is None:
        _ICON_PAUSED = make_hamster_icon(greyed=True)
    return _ICON_PAUSED


class HamsterTray(QSystemTrayIcon):
    _mode_changed = Signal()
    _notify_requested = Signal(str, str)    # (title, body) — thread-safe bridge
    _mini_popup_requested = Signal(str, str) # (title, body) — thread-safe bridge

    def __init__(
        self,
        ctx: "AppContext",
        client: "OllamaClient",
        builder: "PromptBuilder",
        parent=None,
    ) -> None:
        super().__init__(_normal_icon(), parent)
        self._ctx = ctx
        self._client = client
        self._builder = builder
        self._chat_win = None
        self._settings_win = None
        self._plugins_win = None
        self._diag_win = None
        self._notif_win = None
        self._mini_widget = None
        self._mini_worker = None
        self._mini_question = ""
        self._response_windows: list = []
        self._history_win = None

        self.setToolTip("Hamster AI")
        self._build_menu()
        self.activated.connect(self._on_activated)
        self._mode_changed.connect(self._update_mode_ui)
        self._notify_requested.connect(self._show_notification)
        self._mini_popup_requested.connect(self._show_mini_popup)
        self._subscribe_mode_events()
        self._ctx.event_bus.subscribe(NOTIFY, self._on_notify_event)
        self._ctx.event_bus.subscribe("mini_popup", self._on_mini_popup_event)

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.addAction("Open Chat", self._open_chat)
        menu.addSeparator()
        menu.addAction("Notification History", self._open_notification_history)
        menu.addAction("Toggle Mini Widget", self._toggle_mini_widget)
        menu.addSeparator()
        menu.addAction("Settings", self._open_settings)
        menu.addAction("Plugins", self._open_plugins)
        menu.addAction("Diagnostics", self._open_diagnostics)
        menu.addSeparator()
        menu.addAction("Quit", self._quit)
        self.setContextMenu(menu)

    def _subscribe_mode_events(self) -> None:
        bus = self._ctx.event_bus
        for event in (WORK_MODE_ENABLED, PRIVATE_MODE_ENABLED,
                      FOCUS_MODE_ENABLED, GAME_SAFE_MODE_ENABLED,
                      WORK_MODE_DISABLED, PRIVATE_MODE_DISABLED,
                      FOCUS_MODE_DISABLED, GAME_SAFE_MODE_DISABLED):
            bus.subscribe(event, lambda e, d: self._mode_changed.emit())

    def _update_mode_ui(self) -> None:
        modes = self._ctx.modes
        if modes is None:
            return
        active = modes.active_modes()
        if active:
            self.setIcon(_paused_icon())
            self.setToolTip(f"Hamster AI — {', '.join(active)} Mode active")
        else:
            self.setIcon(_normal_icon())
            self.setToolTip("Hamster AI")

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._open_chat()

    def open_chat(self) -> None:
        self._open_chat()

    def _open_chat(self) -> None:
        if self._chat_win is None:
            from app.desktop.chat_window import ChatWindow
            from app.desktop.theme import STYLESHEET
            self._chat_win = ChatWindow(self._ctx, self._client, self._builder)
            self._chat_win.setStyleSheet(STYLESHEET)
            self._ctx.event_bus.subscribe("forget_session", self._on_forget_session)
        if self._chat_win.isVisible():
            self._chat_win.close()
            return
        self._chat_win.show()
        self._chat_win.raise_()
        self._chat_win.activateWindow()

    def _on_notify_event(self, event, data) -> None:
        if isinstance(data, dict):
            title = data.get("title", "Hamster AI")
            body = data.get("body", "")
            self._notify_requested.emit(title, body)

    def _on_mini_popup_event(self, event, data) -> None:
        if isinstance(data, dict):
            title = data.get("title", "Hamster AI")
            body = data.get("body", "")
            self._mini_popup_requested.emit(title, body)

    def _show_notification(self, title: str, body: str) -> None:
        self.showMessage(title, body, QSystemTrayIcon.Information, 6000)

    def _on_forget_session(self, event, data) -> None:
        if self._chat_win:
            self._chat_win.clear_history()

    def _open_settings(self) -> None:
        if self._settings_win is None:
            from app.desktop.settings_window import SettingsWindow
            from app.desktop.theme import STYLESHEET
            self._settings_win = SettingsWindow(self._ctx)
            self._settings_win.setStyleSheet(STYLESHEET)
        self._settings_win.show()
        self._settings_win.raise_()
        self._settings_win.activateWindow()

    def _open_plugins(self) -> None:
        if self._plugins_win is None:
            from app.desktop.plugins_window import PluginsWindow
            from app.desktop.theme import STYLESHEET
            self._plugins_win = PluginsWindow(self._ctx)
            self._plugins_win.setStyleSheet(STYLESHEET)
        self._plugins_win.show()
        self._plugins_win.raise_()
        self._plugins_win.activateWindow()

    def _open_diagnostics(self) -> None:
        if self._diag_win is None:
            from app.desktop.diagnostics_window import DiagnosticsWindow
            from app.desktop.theme import STYLESHEET
            self._diag_win = DiagnosticsWindow(self._ctx)
            self._diag_win.setStyleSheet(STYLESHEET)
        self._diag_win.show()
        self._diag_win.raise_()
        self._diag_win.activateWindow()

    def _open_notification_history(self) -> None:
        if self._notif_win is None:
            from app.desktop.notification_history_window import NotificationHistoryWindow
            from app.desktop.theme import STYLESHEET
            self._notif_win = NotificationHistoryWindow(self._ctx)
            self._notif_win.setStyleSheet(STYLESHEET)
        self._notif_win.show()
        self._notif_win.raise_()
        self._notif_win.activateWindow()

    def _show_mini_popup(self, title: str, body: str) -> None:
        from app.desktop.mini_response_window import MiniResponseWindow
        from PySide6.QtWidgets import QApplication

        win = MiniResponseWindow(self._ctx, title, body)

        # Position above mini widget if visible, otherwise bottom-right corner
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            win.adjustSize()
            x = geo.right() - win.width() - 12
            if self._mini_widget and self._mini_widget.isVisible():
                floor_y = self._mini_widget.y() - 8
            else:
                floor_y = geo.bottom() - 12
            y = floor_y - win.height()
            for existing in self._response_windows:
                if existing.isVisible():
                    y = min(y, existing.y() - win.height() - 8)
            win.move(x, y)

        # Record in history
        from datetime import datetime
        self._ctx.mini_response_history.insert(0, {
            "title": title,
            "body": body,
            "question": self._mini_question if title == "Hamster AI" else "",
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        del self._ctx.mini_response_history[50:]  # cap at 50

        def _remove():
            if win in self._response_windows:
                self._response_windows.remove(win)

        win.closed.connect(_remove)
        self._response_windows.append(win)
        win.show()

    def _toggle_mini_widget(self) -> None:
        if self._mini_widget is None:
            from app.desktop.mini_widget import MiniWidget
            from app.desktop.theme import STYLESHEET
            self._mini_widget = MiniWidget(self._ctx)
            self._mini_widget.setStyleSheet(STYLESHEET)
            self._mini_widget.open_chat_requested.connect(self._open_chat)
            self._mini_widget.message_submitted.connect(self._on_mini_widget_message)
            self._mini_widget.show_history_requested.connect(self._open_mini_history)
        if self._mini_widget.isVisible():
            self._mini_widget.hide()
        else:
            self._mini_widget.show()

    def _on_mini_widget_message(self, text: str) -> None:
        if self._mini_worker is not None:
            self._mini_worker.cancel()
        self._mini_question = text
        snap = self._ctx.pc_context.get_snapshot() if self._ctx.pc_context else None
        messages = self._builder.build([], text, pc_snapshot=snap, app=self._ctx)
        from app.desktop.llm_worker import LLMWorker
        self._mini_worker = LLMWorker(self._client, messages)
        self._mini_worker.response_done.connect(self._on_mini_response_done)
        self._mini_worker.request_error.connect(self._on_mini_response_error)
        self._mini_worker.start()
        if self._mini_widget:
            self._mini_widget.set_status("thinking…")

    def _on_mini_response_done(self, response: str) -> None:
        self._mini_worker = None
        if self._mini_widget:
            self._mini_widget.set_status("Hamster")
        self._mini_popup_requested.emit("Hamster AI", response)

    def _on_mini_response_error(self, error: str) -> None:
        self._mini_worker = None
        if self._mini_widget:
            self._mini_widget.set_status("Hamster")
        self._mini_popup_requested.emit("Hamster AI", f"Error: {error}")

    def _open_mini_history(self) -> None:
        from app.desktop.mini_history_window import MiniHistoryWindow
        if self._history_win is None or not self._history_win.isVisible():
            self._history_win = MiniHistoryWindow(self._ctx)
        self._history_win.refresh()
        self._history_win.show()
        self._history_win.raise_()

    def _quit(self) -> None:
        if self._mini_widget:
            self._mini_widget.save_position()
        self._ctx.stop()
        QApplication.quit()
