from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

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
from app.desktop.icons import make_hamster_pixmap, make_plugin_icon, make_tablet_icon
from app.desktop.llm_worker import LLMWorker
from app.desktop.theme import ACCENT, BG, TEXT, TEXT_MUTED

if TYPE_CHECKING:
    from app.core.app_context import AppContext
    from app.llm.ollama_client import OllamaClient
    from app.llm.prompt_builder import PromptBuilder

_CMD_COLOR = "#6A8F6A"

# Mode pill colours (active fill)
_MODE_COLORS = {
    "private":  "#9B6B9B",
    "focus":    "#5B8FA8",
    "work":     "#C08050",
    "game":     "#5B9B6B",
}


class _CommandPopup(QListWidget):
    command_chosen = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(
            f"QListWidget {{ background: {BG}; border: 1.5px solid #D4C4B0; "
            f"color: {TEXT}; font-size: 12px; padding: 2px; border-radius: 6px; }}"
            f"QListWidget::item {{ padding: 5px 10px; }}"
            f"QListWidget::item:selected {{ background: #F2E0C8; color: {TEXT}; }}"
            f"QListWidget::item:hover {{ background: #FAF0E6; }}"
        )
        self.itemClicked.connect(lambda item: self.command_chosen.emit(item.data(Qt.UserRole)))

    def populate(self, commands: list[tuple[str, str]], prefix: str) -> None:
        self.clear()
        prefix_lower = prefix.lower()
        for name, desc in commands:
            full = f"/{name}"
            if not full.startswith(prefix_lower):
                continue
            display = f"{full}  —  {desc}" if desc else full
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, full)
            self.addItem(item)
        if self.count():
            self.setCurrentRow(0)

    def reposition(self, anchor: QWidget) -> None:
        row_h = self.sizeHintForRow(0) if self.count() else 26
        popup_h = min(row_h * self.count() + 8, 230)
        gp = anchor.mapToGlobal(anchor.rect().topLeft())
        self.setFixedWidth(anchor.width())
        self.move(gp.x(), gp.y() - popup_h)
        self.resize(anchor.width(), popup_h)

    def move_selection(self, delta: int) -> None:
        if not self.count():
            return
        self.setCurrentRow((self.currentRow() + delta) % self.count())

    def accept_selection(self) -> str | None:
        item = self.currentItem() or (self.item(0) if self.count() else None)
        return item.data(Qt.UserRole) if item else None


class _CommandInput(QLineEdit):
    def __init__(self, popup: _CommandPopup, parent=None) -> None:
        super().__init__(parent)
        self._popup = popup

    def event(self, ev) -> bool:
        # Qt consumes Tab for focus traversal before keyPressEvent sees it,
        # so intercept it here while the popup is open.
        if (ev.type() == QEvent.KeyPress and ev.key() == Qt.Key_Tab
                and self._popup.isVisible()):
            cmd = self._popup.accept_selection()
            if cmd:
                self.setText(cmd + " ")
                self.setCursorPosition(len(self.text()))
            self._popup.hide()
            return True
        return super().event(ev)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if self._popup.isVisible():
            if key == Qt.Key_Up:
                self._popup.move_selection(-1)
                event.accept()
                return
            if key == Qt.Key_Down:
                self._popup.move_selection(1)
                event.accept()
                return
            if key == Qt.Key_Escape:
                self._popup.hide()
                event.accept()
                return
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._popup.hide()
        super().keyPressEvent(event)


def _pill_style(color: str, active: bool) -> str:
    if active:
        return (
            f"QPushButton {{ background: {color}; color: white; border: none; "
            f"border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {color}CC; }}"
        )
    return (
        f"QPushButton {{ background: transparent; color: {color}; "
        f"border: 1.5px solid {color}; border-radius: 10px; padding: 3px 10px; "
        f"font-size: 11px; font-weight: bold; }}"
        f"QPushButton:hover {{ background: {color}22; }}"
    )


_FILE_DROP_MAX_LINES = 2000
_FILE_DROP_MAX_KB = 512
_SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".log", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".sql", ".html", ".css", ".xml", ".csv",
    ".sh", ".bat", ".ps1", ".rs", ".go", ".java", ".c", ".cpp", ".h",
}


class ChatWindow(QWidget):
    closed = Signal()
    _mode_changed = Signal()   # emitted from any thread, processed on main thread

    def __init__(
        self,
        ctx: "AppContext",
        client: "OllamaClient",
        builder: "PromptBuilder",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._client = client
        self._builder = builder
        self._history: list[dict[str, str]] = []
        self._worker: LLMWorker | None = None
        self._pending_text: str = ""
        self._stream_cursor: QTextCursor | None = None
        self._settings_win = None
        self._plugins_win = None
        self._diag_win = None
        self._attached_file_content: str | None = None

        self._setup_window()
        self._setup_ui()
        self._mode_changed.connect(self._sync_mode_buttons)
        self._subscribe_mode_events()
        self._sync_mode_buttons()

    def _setup_window(self) -> None:
        self.setWindowTitle("Hamster AI")
        self.setMinimumSize(420, 540)
        self.resize(480, 660)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self.setAcceptDrops(True)
        from app.desktop.icons import make_hamster_icon
        self.setWindowIcon(make_hamster_icon())

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(6)

        # ── Header ────────────────────────────────────────────────────────────
        _icon_btn_style = (
            f"QPushButton {{ background: transparent; border: none; color: {TEXT_MUTED}; "
            f"font-size: 15px; border-radius: 4px; padding: 1px 4px; }}"
            f"QPushButton:hover {{ background: #F2E0C8; color: {ACCENT}; }}"
            f"QPushButton:pressed {{ background: #E8D0B0; }}"
        )
        header = QHBoxLayout()
        header.setSpacing(8)
        icon_label = QLabel()
        icon_label.setPixmap(make_hamster_pixmap(22))
        icon_label.setFixedSize(22, 22)
        icon_label.setStyleSheet("background: transparent;")
        title = QLabel("Hamster AI")
        title.setStyleSheet(
            f"font-weight: bold; font-size: 15px; color: {ACCENT}; background: transparent;"
        )
        self._status_label = QLabel("ready")
        self._status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._status_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        diag_btn = QPushButton()
        diag_btn.setIcon(make_tablet_icon(20))
        diag_btn.setFixedSize(26, 26)
        diag_btn.setToolTip("Diagnostics")
        diag_btn.setCursor(Qt.PointingHandCursor)
        diag_btn.setStyleSheet(_icon_btn_style)
        diag_btn.clicked.connect(self._open_diagnostics)
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(26, 26)
        settings_btn.setToolTip("Settings")
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.setStyleSheet(_icon_btn_style)
        settings_btn.clicked.connect(self._open_settings)
        header.addWidget(icon_label)
        header.addWidget(title)
        header.addStretch()
        plugins_btn = QPushButton()
        plugins_btn.setIcon(make_plugin_icon(20))
        plugins_btn.setFixedSize(26, 26)
        plugins_btn.setToolTip("Plugins")
        plugins_btn.setCursor(Qt.PointingHandCursor)
        plugins_btn.setStyleSheet(_icon_btn_style)
        plugins_btn.clicked.connect(self._open_plugins)
        header.addWidget(self._status_label)
        header.addWidget(diag_btn)
        header.addWidget(plugins_btn)
        header.addWidget(settings_btn)
        root.addLayout(header)

        # ── Mode bar ──────────────────────────────────────────────────────────
        mode_bar = QHBoxLayout()
        mode_bar.setSpacing(6)
        mode_bar.setContentsMargins(0, 0, 0, 4)

        self._btn_private = QPushButton("Private")
        self._btn_focus   = QPushButton("Focus")
        self._btn_work    = QPushButton("Work")
        self._btn_game    = QPushButton("Game Safe")

        for btn in (self._btn_private, self._btn_focus, self._btn_work, self._btn_game):
            btn.setFixedHeight(22)
            btn.setCursor(Qt.PointingHandCursor)

        self._btn_private.setToolTip("Toggle Private Mode — nothing logged or stored")
        self._btn_focus.setToolTip("Toggle Focus Mode (30 min) — pauses notifications")
        self._btn_work.setToolTip("Toggle Work Mode — auto-detected from Horizon Client")
        self._btn_game.setToolTip("Toggle Game Safe Mode — auto-detected from anti-cheat processes")

        self._btn_private.clicked.connect(self._toggle_private)
        self._btn_focus.clicked.connect(self._toggle_focus)
        self._btn_work.clicked.connect(self._toggle_work)
        self._btn_game.clicked.connect(self._toggle_game)

        mode_bar.addWidget(self._btn_private)
        mode_bar.addWidget(self._btn_focus)
        mode_bar.addWidget(self._btn_work)
        mode_bar.addWidget(self._btn_game)
        mode_bar.addStretch()
        root.addLayout(mode_bar)

        # ── Chat display ──────────────────────────────────────────────────────
        self._chat = QTextEdit()
        self._chat.setReadOnly(True)
        self._chat.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._chat)

        # ── File attachment indicator ─────────────────────────────────────────
        self._file_label = QLabel("")
        self._file_label.setStyleSheet(
            f"color: #6A8F6A; font-size: 11px; font-style: italic; background: transparent;"
        )
        self._file_label.hide()
        root.addWidget(self._file_label)

        # ── Input row ─────────────────────────────────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(6)
        self._cmd_popup = _CommandPopup()
        self._input = _CommandInput(self._cmd_popup)
        self._input.setPlaceholderText("Type a message or /command…")
        self._input.returnPressed.connect(self._send)
        self._input.textChanged.connect(self._on_input_changed)
        self._send_btn = QPushButton("Send")
        self._send_btn.setFixedWidth(68)
        self._send_btn.clicked.connect(self._send)
        row.addWidget(self._input)
        row.addWidget(self._send_btn)
        root.addLayout(row)

    # ── Mode button logic ─────────────────────────────────────────────────────

    def _subscribe_mode_events(self) -> None:
        bus = self._ctx.event_bus
        for event in (PRIVATE_MODE_ENABLED, PRIVATE_MODE_DISABLED,
                      FOCUS_MODE_ENABLED, FOCUS_MODE_DISABLED,
                      WORK_MODE_ENABLED, WORK_MODE_DISABLED,
                      GAME_SAFE_MODE_ENABLED, GAME_SAFE_MODE_DISABLED):
            bus.subscribe(event, lambda e, d: self._mode_changed.emit())

    def _sync_mode_buttons(self) -> None:
        modes = self._ctx.modes
        if modes is None:
            return
        self._set_pill(self._btn_private, "private", modes.private_mode)
        self._set_pill(self._btn_focus,   "focus",   modes.focus_mode)
        self._set_pill(self._btn_work,    "work",    modes.work_mode)
        self._set_pill(self._btn_game,    "game",    modes.game_safe_mode)

        active = modes.active_modes()
        self._status_label.setText(
            f"{', '.join(active)} Mode" if active else "ready"
        )

    def _set_pill(self, btn: QPushButton, key: str, active: bool) -> None:
        btn.setStyleSheet(_pill_style(_MODE_COLORS[key], active))

    def _toggle_private(self) -> None:
        m = self._ctx.modes
        if m.private_mode:
            m.disable_private_mode()
        else:
            m.enable_private_mode()

    def _toggle_focus(self) -> None:
        m = self._ctx.modes
        if m.focus_mode:
            m.disable_focus_mode()
        else:
            m.enable_focus_mode(minutes=30)

    def _toggle_work(self) -> None:
        m = self._ctx.modes
        if m.work_mode:
            m.disable_work_mode()
        else:
            m.enable_work_mode()

    def _toggle_game(self) -> None:
        m = self._ctx.modes
        if m.game_safe_mode:
            m.disable_game_safe_mode()
        else:
            m.enable_game_safe_mode()

    # ── Message rendering ─────────────────────────────────────────────────────

    def _ts(self) -> str:
        if not self._ctx.settings.get("chat_timestamps_enabled", True):
            return ""
        from datetime import datetime
        return datetime.now().strftime("[%H:%M] ")

    def _add_user_bubble(self, text: str) -> None:
        cursor = self._chat.textCursor()
        cursor.movePosition(QTextCursor.End)
        if not self._chat.document().isEmpty():
            cursor.insertBlock()

        label_fmt = QTextCharFormat()
        label_fmt.setForeground(QColor(TEXT_MUTED))
        cursor.insertText(f"{self._ts()}You: ", label_fmt)

        body_fmt = QTextCharFormat()
        body_fmt.setForeground(QColor(TEXT))
        cursor.insertText(text, body_fmt)

        self._chat.setTextCursor(cursor)
        self._chat.ensureCursorVisible()

    def _add_command_response(self, text: str) -> None:
        cursor = self._chat.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertBlock()

        label_fmt = QTextCharFormat()
        label_fmt.setForeground(QColor(_CMD_COLOR))
        label_fmt.setFontWeight(QFont.Bold)
        cursor.insertText(f"{self._ts()}Hamster: ", label_fmt)

        body_fmt = QTextCharFormat()
        body_fmt.setForeground(QColor(_CMD_COLOR))
        body_fmt.setFontItalic(True)
        cursor.insertText(text, body_fmt)

        self._chat.setTextCursor(cursor)
        self._chat.ensureCursorVisible()

    def _start_assistant_bubble(self) -> None:
        cursor = self._chat.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertBlock()

        label_fmt = QTextCharFormat()
        label_fmt.setForeground(QColor(ACCENT))
        label_fmt.setFontWeight(QFont.Bold)
        cursor.insertText(f"{self._ts()}Hamster: ", label_fmt)

        body_fmt = QTextCharFormat()
        body_fmt.setForeground(QColor(TEXT))
        body_fmt.setFontWeight(QFont.Normal)
        cursor.setCharFormat(body_fmt)

        self._stream_cursor = cursor
        self._chat.setTextCursor(cursor)
        self._chat.ensureCursorVisible()

    def _append_chunk(self, chunk: str) -> None:
        if self._stream_cursor:
            self._stream_cursor.insertText(chunk)
            self._chat.ensureCursorVisible()

    # ── Command autocomplete ──────────────────────────────────────────────────

    def _on_input_changed(self, text: str) -> None:
        if text.startswith("/") and self._ctx.commands:
            cmds = self._ctx.commands.list_commands()
            self._cmd_popup.populate(cmds, text)
            if self._cmd_popup.count():
                self._cmd_popup.reposition(self._input)
                self._cmd_popup.show()
                return
        self._cmd_popup.hide()

    # ── Send flow ─────────────────────────────────────────────────────────────

    def _send(self) -> None:
        text = self._input.text().strip()
        if not text or self._worker is not None:
            return

        self._input.clear()
        self._add_user_bubble(text)

        if self._ctx.commands and self._ctx.commands.is_command(text):
            from app.core.event_bus import COMMAND_RECEIVED
            self._ctx.event_bus.emit(COMMAND_RECEIVED, {"text": text})
            response = self._ctx.commands.dispatch(text, self._ctx)
            self._add_command_response(response)
            return

        effective_text = text
        if self._attached_file_content:
            effective_text = f"{self._attached_file_content}\n\nUser question: {text}"
            self._attached_file_content = None
            self._file_label.hide()

        self._pending_text = text
        self._set_busy(True)
        self._start_assistant_bubble()

        from app.core.event_bus import USER_MESSAGE
        self._ctx.event_bus.emit(USER_MESSAGE, {"text": text})

        snap = self._ctx.pc_context.get_snapshot() if self._ctx.pc_context else None
        messages = self._builder.build(self._history, effective_text, pc_snapshot=snap, app=self._ctx)
        self._worker = LLMWorker(self._client, messages)
        self._worker.chunk_received.connect(self._append_chunk)
        self._worker.response_done.connect(self._on_done)
        self._worker.request_error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, full_response: str) -> None:
        self._history.append({"role": "user", "content": self._pending_text})
        self._history.append({"role": "assistant", "content": full_response})
        self._pending_text = ""
        from app.core.event_bus import ASSISTANT_MESSAGE
        self._ctx.event_bus.emit(ASSISTANT_MESSAGE, {"text": full_response})
        self._finish()

    def _on_error(self, error_msg: str) -> None:
        if self._stream_cursor:
            err_fmt = QTextCharFormat()
            err_fmt.setForeground(QColor("#CC4444"))
            self._stream_cursor.insertText(f"[Error: {error_msg}]", err_fmt)
        self._ctx.logger.error(f"LLM error: {error_msg}")
        self._finish()

    def _finish(self) -> None:
        self._worker = None
        self._stream_cursor = None
        self._set_busy(False)
        self._input.setFocus()

    def _set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._send_btn.setEnabled(not busy)
        if not busy:
            self._sync_mode_buttons()
        else:
            self._status_label.setText("thinking…")

    # ── Header button actions ─────────────────────────────────────────────────

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

    # ── File drop ─────────────────────────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        from pathlib import Path
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            self._add_command_response(
                f"File type '{path.suffix}' not supported. "
                f"Supported: text, code, config, and data files."
            )
            return
        size_kb = path.stat().st_size / 1024
        if size_kb > _FILE_DROP_MAX_KB:
            self._add_command_response(
                f"File too large ({size_kb:.0f} KB). Limit is {_FILE_DROP_MAX_KB} KB."
            )
            return
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            self._add_command_response(f"Could not read file: {exc}")
            return
        lines = content.splitlines()
        if len(lines) > _FILE_DROP_MAX_LINES:
            self._add_command_response(
                f"File has {len(lines)} lines — truncating to {_FILE_DROP_MAX_LINES}."
            )
            content = "\n".join(lines[:_FILE_DROP_MAX_LINES])
            lines = lines[:_FILE_DROP_MAX_LINES]
        self._attached_file_content = f"[File: {path.name}]\n{content}"
        self._file_label.setText(f"Attached: {path.name} ({len(lines)} lines) — will be sent with your next message")
        self._file_label.show()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        pending = self._ctx.pending_mini_responses[:]
        self._ctx.pending_mini_responses.clear()
        for item in pending:
            title = item.get("title", "Notification")
            body = item.get("body", "")
            self._add_command_response(f"[Missed {title}] {body}")

    def closeEvent(self, event) -> None:
        self._cmd_popup.hide()
        if self._worker:
            self._worker.cancel()
            self._worker.wait(2000)
        self.closed.emit()
        event.accept()

    def clear_history(self) -> None:
        self._history.clear()
        self._chat.clear()

    def update_mode_status(self, active_modes: list[str]) -> None:
        self._sync_mode_buttons()
