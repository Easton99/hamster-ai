from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

if TYPE_CHECKING:
    from app.core.app_context import AppContext


class MiniOverlay(QWidget):
    open_chat_requested = Signal()

    def __init__(self, ctx: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._setup_window()
        self._setup_ui()
        self._subscribe()
        self._reposition()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        width = self._ctx.settings.get("mini_overlay_width", 320)
        self.setFixedHeight(32)
        self.setFixedWidth(width)

    def _setup_ui(self) -> None:
        from app.desktop.theme import ACCENT, BG, TEXT_MUTED

        self.setStyleSheet(
            f"QWidget {{ background: {BG}; border-radius: 6px; }}"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)

        self._text = QLabel("Hamster AI")
        self._text.setStyleSheet(
            f"font-size: 11px; color: {TEXT_MUTED}; background: transparent;"
        )
        self._text.setCursor(Qt.PointingHandCursor)
        self._text.mousePressEvent = lambda _: self.open_chat_requested.emit()
        layout.addWidget(self._text)

    def _subscribe(self) -> None:
        bus = self._ctx.event_bus
        bus.subscribe("assistant_message", self._on_message)
        bus.subscribe("notify", self._on_notify)

    def _on_message(self, event, data) -> None:
        if self._is_protected():
            return
        text = data.get("text", "") if isinstance(data, dict) else ""
        self._show_text(text[:80])

    def _on_notify(self, event, data) -> None:
        if self._is_protected():
            return
        body = data.get("body", "") if isinstance(data, dict) else ""
        self._show_text(body[:80])

    def _show_text(self, text: str) -> None:
        self._text.setText(text)
        self.show()
        secs = self._ctx.settings.get("mini_overlay_auto_hide_seconds", 8)
        self._hide_timer.start(secs * 1000)

    def _is_protected(self) -> bool:
        modes = self._ctx.modes
        return bool(modes and (modes.work_mode or modes.private_mode or modes.game_safe_mode))

    def _reposition(self) -> None:
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        position = self._ctx.settings.get("mini_overlay_position", "top-right")

        if "top" in position:
            y = geo.top() + 4
        else:
            y = geo.bottom() - self.height() - 4

        if "right" in position:
            x = geo.right() - self.width() - 4
        else:
            x = geo.left() + 4

        self.move(x, y)
