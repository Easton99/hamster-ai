from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.core.app_context import AppContext

_AUTO_CLOSE_SECS = 10


class MiniResponseWindow(QWidget):
    """Small always-on-top popup for quick responses and reminder notifications.

    X button → dismissed (no pending entry).
    Timer expiry → stored in ctx.pending_mini_responses for next chat open.
    """

    closed = Signal()

    def __init__(self, ctx: "AppContext", title: str, body: str, parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._title_text = title
        self._body_text = body
        self._drag_pos = None
        self._remaining = _AUTO_CLOSE_SECS
        self._setup_window()
        self._setup_ui()
        self._start_timer()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(320)

    def _setup_ui(self) -> None:
        from app.desktop.theme import ACCENT, BG, TEXT

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setObjectName("mrw_title_bar")
        title_bar.setStyleSheet(f"QWidget#mrw_title_bar {{ background: {ACCENT}; }}")
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(12, 6, 6, 6)
        tb.setSpacing(6)

        title_lbl = QLabel(self._title_text)
        title_lbl.setStyleSheet(
            "color: white; font-weight: bold; font-size: 12px; background: transparent;"
        )

        self._timer_lbl = QLabel(f"{_AUTO_CLOSE_SECS}s")
        self._timer_lbl.setStyleSheet(
            "color: rgba(255,255,255,180); font-size: 11px; background: transparent;"
        )

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            " color: white; font-size: 13px; }"
            "QPushButton:hover { background: rgba(255,255,255,50); border-radius: 4px; }"
        )
        close_btn.clicked.connect(self._on_dismiss)

        tb.addWidget(title_lbl)
        tb.addStretch()
        tb.addWidget(self._timer_lbl)
        tb.addWidget(close_btn)
        root.addWidget(title_bar)

        # Body
        body_widget = QWidget()
        body_widget.setStyleSheet(f"background: {BG};")
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(12, 10, 12, 12)

        body_lbl = QLabel(self._body_text)
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; background: transparent;"
        )
        body_lbl.setMaximumWidth(296)
        body_layout.addWidget(body_lbl)
        root.addWidget(body_widget)

        self.adjustSize()

    def _start_timer(self) -> None:
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start()

    def _on_tick(self) -> None:
        self._remaining -= 1
        self._timer_lbl.setText(f"{self._remaining}s")
        if self._remaining <= 0:
            self._tick_timer.stop()
            self._on_auto_close()

    def _on_dismiss(self) -> None:
        self._tick_timer.stop()
        self.closed.emit()
        self.close()

    def _on_auto_close(self) -> None:
        self._ctx.pending_mini_responses.append({
            "title": self._title_text,
            "body": self._body_text,
        })
        self.closed.emit()
        self.close()

    # ── Dragging ──────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
