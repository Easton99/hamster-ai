from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from app.core.app_context import AppContext


class MiniHistoryWindow(QWidget):
    """Floating list of recent mini-widget responses and reminder popups."""

    def __init__(self, ctx: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._setup_window()
        self._setup_ui()
        self._reposition()

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(380)

    def _setup_ui(self) -> None:
        from app.desktop.theme import ACCENT, BG, BORDER, TEXT, TEXT_MUTED

        self.setStyleSheet(
            f"QWidget {{ background: {BG}; color: {TEXT}; font-size: 12px; }}"
            f"QListWidget {{ border: none; background: {BG}; }}"
            f"QListWidget::item {{ padding: 8px 10px; border-bottom: 1px solid {BORDER}; }}"
            f"QListWidget::item:selected {{ background: transparent; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setObjectName("mhw_title_bar")
        title_bar.setStyleSheet(f"QWidget#mhw_title_bar {{ background: {ACCENT}; }}")
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(12, 6, 6, 6)

        title_lbl = QLabel("Recent Responses")
        title_lbl.setStyleSheet(
            "color: white; font-weight: bold; font-size: 12px; background: transparent;"
        )

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            " color: white; font-size: 13px; }"
            "QPushButton:hover { background: rgba(255,255,255,50); border-radius: 4px; }"
        )
        close_btn.clicked.connect(self.close)

        tb.addWidget(title_lbl)
        tb.addStretch()
        tb.addWidget(close_btn)
        root.addWidget(title_bar)

        self._list = QListWidget()
        self._list.setWordWrap(True)
        self._list.setSpacing(0)
        root.addWidget(self._list)

        empty_lbl = QLabel("No responses yet.")
        empty_lbl.setAlignment(Qt.AlignCenter)
        empty_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; padding: 16px;")
        self._empty_lbl = empty_lbl
        root.addWidget(empty_lbl)

        self.setFixedHeight(400)

    def refresh(self) -> None:
        from app.desktop.theme import ACCENT, TEXT, TEXT_MUTED

        self._list.clear()
        history = self._ctx.mini_response_history
        self._empty_lbl.setVisible(len(history) == 0)
        self._list.setVisible(len(history) > 0)

        for entry in history:
            title = entry.get("title", "")
            body = entry.get("body", "")
            question = entry.get("question", "")
            ts = entry.get("timestamp", "")

            if question:
                display = f"{ts}  {title}\nQ: {question}\n{body}"
            else:
                display = f"{ts}  {title}\n{body}"

            item = QListWidgetItem(display)
            item.setForeground(TEXT)
            self._list.addItem(item)

    def _reposition(self) -> None:
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.right() - self.width() - 12
        y = geo.bottom() - self.height() - 70
        self.move(x, y)
