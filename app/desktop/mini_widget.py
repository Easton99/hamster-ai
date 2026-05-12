from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

if TYPE_CHECKING:
    from app.core.app_context import AppContext


class MiniWidget(QWidget):
    open_chat_requested = Signal()
    show_history_requested = Signal()
    message_submitted = Signal(str)

    def __init__(self, ctx: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._dragging = False
        self._drag_pos = None
        self._setup_window()
        self._setup_ui()
        self._subscribe()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        opacity = self._ctx.settings.get("mini_widget_opacity", 0.9)
        self.setWindowOpacity(opacity)

    def _reposition(self) -> None:
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if not screen:
            return
        self.adjustSize()
        geo = screen.availableGeometry()
        corner = self._ctx.settings.get("mini_widget_position", "bottom-right")
        offset_x = self._ctx.settings.get("mini_widget_offset_x", 12)
        offset_y = self._ctx.settings.get("mini_widget_offset_y", 12)
        w = self.width() or 340
        h = self.height() or 44
        x = geo.right() - w - offset_x if "right" in corner else geo.left() + offset_x
        y = geo.bottom() - h - offset_y if "bottom" in corner else geo.top() + offset_y
        self.move(x, y)

    def _setup_ui(self) -> None:
        from app.desktop.theme import ACCENT, BG, TEXT, TEXT_MUTED

        self.setStyleSheet(
            f"QWidget {{ background: {BG}; border-radius: 12px; }}"
            f"QLineEdit {{ background: white; border: 1px solid #D4C4B0;"
            f" border-radius: 6px; padding: 4px 8px; color: {TEXT}; font-size: 12px; }}"
            f"QPushButton#hist_btn {{ background: transparent; border: none;"
            f" color: {TEXT_MUTED}; font-size: 14px; padding: 0px 2px; }}"
            f"QPushButton#hist_btn:hover {{ color: {ACCENT}; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self._status_lbl = QLabel("Hamster")
        self._status_lbl.setStyleSheet(
            f"font-weight: bold; font-size: 12px; color: {ACCENT};"
            " background: transparent;"
        )
        self._status_lbl.setCursor(Qt.PointingHandCursor)
        self._status_lbl.mousePressEvent = lambda _: self.open_chat_requested.emit()

        self._input = QLineEdit()
        self._input.setPlaceholderText("Quick message…")
        self._input.setFixedWidth(160)
        self._input.setFixedHeight(34)
        self._input.returnPressed.connect(self._on_submit)

        self._hist_btn = QPushButton("⏱")
        self._hist_btn.setObjectName("hist_btn")
        self._hist_btn.setFixedSize(24, 24)
        self._hist_btn.setToolTip("Recent responses")
        self._hist_btn.setCursor(Qt.PointingHandCursor)
        self._hist_btn.clicked.connect(self.show_history_requested.emit)

        layout.addWidget(self._status_lbl)
        layout.addWidget(self._input)
        layout.addWidget(self._hist_btn)
        self.adjustSize()
        self._reposition()

    def _subscribe(self) -> None:
        bus = self._ctx.event_bus
        bus.subscribe("work_mode_enabled",     lambda e, d: self._update_visibility())
        bus.subscribe("work_mode_disabled",    lambda e, d: self._update_visibility())
        bus.subscribe("private_mode_enabled",  lambda e, d: self._update_visibility())
        bus.subscribe("private_mode_disabled", lambda e, d: self._update_visibility())
        bus.subscribe("game_safe_mode_enabled",  lambda e, d: self._update_visibility())
        bus.subscribe("game_safe_mode_disabled", lambda e, d: self._update_visibility())

    def _on_submit(self) -> None:
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.message_submitted.emit(text)

    def _update_visibility(self) -> None:
        modes = self._ctx.modes
        if modes and (modes.work_mode or modes.private_mode or modes.game_safe_mode):
            self.hide()
        else:
            self.show()

    def set_status(self, text: str) -> None:
        self._status_lbl.setText(text)

    def save_position(self) -> None:
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        corner = self._ctx.settings.get("mini_widget_position", "bottom-right")
        pos = self.pos()
        w, h = self.width(), self.height()
        offset_x = (geo.right() - pos.x() - w) if "right" in corner else (pos.x() - geo.left())
        offset_y = (geo.bottom() - pos.y() - h) if "bottom" in corner else (pos.y() - geo.top())
        self._ctx.settings.set("mini_widget_offset_x", max(0, offset_x))
        self._ctx.settings.set("mini_widget_offset_y", max(0, offset_y))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False
        self.save_position()
