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

from app.desktop.icons import make_hamster_icon
from app.desktop.theme import ACCENT, TEXT_MUTED

if TYPE_CHECKING:
    from app.core.app_context import AppContext


class NotificationHistoryWindow(QWidget):
    def __init__(self, ctx: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("Hamster AI — Notification History")
        self.setWindowIcon(make_hamster_icon())
        self.setMinimumSize(460, 360)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)

        heading = QLabel("Notification History")
        heading.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {ACCENT}; background: transparent;"
        )
        root.addWidget(heading)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        root.addWidget(self._list)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        clear_btn = QPushButton("Clear All")
        clear_btn.setStyleSheet(
            "background: #C06060; color: white; font-weight: bold;"
            " border-radius: 6px; padding: 6px 14px;"
        )
        clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(clear_btn)
        root.addLayout(btn_row)

    def _reload(self) -> None:
        self._list.clear()
        nh = self._ctx.notification_history
        if not nh:
            return
        entries = nh.list_recent(100)
        for e in entries:
            ts = e.timestamp[:16]
            label = f"[{ts}]  {e.type.upper():<10}  {e.content}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, e.id)
            if e.dismissed:
                item.setForeground(Qt.gray)
            self._list.addItem(item)

    def _clear_all(self) -> None:
        nh = self._ctx.notification_history
        if nh:
            nh.clear()
        self._list.clear()

    def showEvent(self, event) -> None:
        self._reload()
        super().showEvent(event)
