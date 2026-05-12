from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.desktop.icons import make_hamster_icon

if TYPE_CHECKING:
    from app.core.app_context import AppContext


class SettingsWindow(QWidget):
    def __init__(self, ctx: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._setup_window()
        self._setup_ui()
        self._load()

    def _setup_window(self) -> None:
        self.setWindowTitle("Hamster AI — Settings")
        self.setWindowIcon(make_hamster_icon())
        self.setMinimumSize(480, 480)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_general_tab(), "General")
        self._tabs.addTab(self._build_appearance_tab(), "Appearance")
        self._tabs.addTab(self._build_memory_tab(), "Memory")
        self._tabs.addTab(self._build_personality_tab(), "Personality")
        root.addWidget(self._tabs)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "background: #C4A882; color: white; font-weight: bold;"
            " border-radius: 6px; padding: 6px 16px;"
        )
        cancel_btn.clicked.connect(self.close)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    # ── General tab ───────────────────────────────────────────────────────────

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self._model = QComboBox()
        self._model.setEditable(True)
        self._model_refresh_btn = QPushButton("↻")
        self._model_refresh_btn.setFixedWidth(32)
        self._model_refresh_btn.setToolTip("Refresh model list from Ollama")
        self._model_refresh_btn.clicked.connect(self._refresh_models)
        model_row = QHBoxLayout()
        model_row.addWidget(self._model)
        model_row.addWidget(self._model_refresh_btn)
        form.addRow("Model:", model_row)

        self._ollama_url = QLineEdit()
        form.addRow("Ollama URL:", self._ollama_url)

        self._log_level = QComboBox()
        self._log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        form.addRow("Log level:", self._log_level)

        layout.addLayout(form)

        self._start_windows = QCheckBox("Start with Windows")
        self._greet_startup = QCheckBox("Greet on startup")
        self._chat_timestamps = QCheckBox("Show timestamps in chat")
        layout.addWidget(self._start_windows)
        layout.addWidget(self._greet_startup)
        layout.addWidget(self._chat_timestamps)

        delay_row = QHBoxLayout()
        delay_label = QLabel("Startup delay:")
        delay_label.setFixedWidth(110)
        self._startup_delay = QSpinBox()
        self._startup_delay.setRange(10, 120)
        self._startup_delay.setSuffix("  seconds")
        delay_row.addWidget(delay_label)
        delay_row.addWidget(self._startup_delay)
        delay_row.addStretch()
        layout.addLayout(delay_row)
        layout.addStretch()
        return w

    # ── Appearance tab ────────────────────────────────────────────────────────

    def _build_appearance_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(10)

        self._theme = QComboBox()
        self._theme.addItem("Light (Soft Hamster)", "soft_hamster_minimal")
        self._theme.addItem("Dark Hamster", "dark_hamster")
        self._theme.addItem("High Contrast", "high_contrast")
        form.addRow("Theme:", self._theme)

        self._hotkey_edit = QLineEdit()
        self._hotkey_edit.setPlaceholderText("e.g. Ctrl+Shift+H")
        form.addRow("Global hotkey:", self._hotkey_edit)

        layout.addLayout(form)

        self._hotkey_enabled = QCheckBox("Enable global hotkey")
        layout.addWidget(self._hotkey_enabled)

        mini_lbl = QLabel("Mini Widget & Overlay")
        mini_lbl.setStyleSheet("font-weight: bold; background: transparent;")
        layout.addWidget(mini_lbl)

        self._mini_widget_enabled = QCheckBox("Show mini widget on startup")
        layout.addWidget(self._mini_widget_enabled)

        widget_pos_row = QFormLayout()
        widget_pos_row.setLabelAlignment(Qt.AlignRight)
        self._widget_position = QComboBox()
        for pos in ["bottom-right", "bottom-left", "top-right", "top-left"]:
            self._widget_position.addItem(pos, pos)
        widget_pos_row.addRow("Widget corner:", self._widget_position)

        widget_offset_row = QHBoxLayout()
        self._widget_offset_x = QSpinBox()
        self._widget_offset_x.setRange(0, 500)
        self._widget_offset_x.setSuffix(" px")
        self._widget_offset_y = QSpinBox()
        self._widget_offset_y.setRange(0, 500)
        self._widget_offset_y.setSuffix(" px")
        widget_offset_row.addWidget(QLabel("Offset X:"))
        widget_offset_row.addWidget(self._widget_offset_x)
        widget_offset_row.addWidget(QLabel("Y:"))
        widget_offset_row.addWidget(self._widget_offset_y)
        widget_offset_row.addStretch()
        widget_pos_row.addRow("", widget_offset_row)
        layout.addLayout(widget_pos_row)

        self._mini_overlay_enabled = QCheckBox("Show mini overlay")
        layout.addWidget(self._mini_overlay_enabled)

        overlay_pos_row = QFormLayout()
        overlay_pos_row.setLabelAlignment(Qt.AlignRight)
        self._overlay_position = QComboBox()
        for pos in ["top-right", "top-left", "bottom-right", "bottom-left"]:
            self._overlay_position.addItem(pos, pos)
        overlay_pos_row.addRow("Overlay position:", self._overlay_position)

        self._overlay_hide_secs = QSpinBox()
        self._overlay_hide_secs.setRange(2, 60)
        self._overlay_hide_secs.setSuffix(" seconds")
        overlay_pos_row.addRow("Auto-hide after:", self._overlay_hide_secs)

        layout.addLayout(overlay_pos_row)
        layout.addStretch()
        return w

    # ── Memory tab ────────────────────────────────────────────────────────────

    def _build_memory_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(12)

        search_row = QHBoxLayout()
        self._mem_search = QLineEdit()
        self._mem_search.setPlaceholderText("Search memories, notes, todos…")
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._do_memory_search)
        search_row.addWidget(self._mem_search)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        from PySide6.QtWidgets import QListWidget
        self._mem_results = QListWidget()
        self._mem_results.setAlternatingRowColors(True)
        layout.addWidget(self._mem_results)

        hint = QLabel(
            "Use /remember, /todo, /note to add items.\n"
            "Use /show-memories #tag to filter by tag.\n"
            "Tags: add a #tag at the end when saving (e.g. /remember dark mode #preferences)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 11px; background: transparent;")
        layout.addWidget(hint)
        return w

    # ── Personality tab ───────────────────────────────────────────────────────

    def _build_personality_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(8)

        from app.desktop.personality_editor import PersonalityEditor
        self._personality_editor = PersonalityEditor(self._ctx)
        self._personality_editor.profile_changed.connect(
            lambda name: self._ctx.settings.set("personality", name)
        )
        layout.addWidget(self._personality_editor)
        return w

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        s = self._ctx.settings

        # General
        model = s.get("model", "llama3.2:3b")
        self._model.addItem(model)
        self._model.setCurrentText(model)
        self._ollama_url.setText(s.get("ollama_url", "http://localhost:11434"))
        idx = self._log_level.findText(s.get("log_level", "INFO"))
        self._log_level.setCurrentIndex(max(idx, 0))
        self._start_windows.setChecked(s.get("start_with_windows", False))
        self._greet_startup.setChecked(s.get("greet_on_startup", True))
        self._chat_timestamps.setChecked(s.get("chat_timestamps_enabled", True))
        self._startup_delay.setValue(s.get("startup_delay_seconds", 30))

        # Appearance
        theme = s.get("theme", "soft_hamster_minimal")
        idx = self._theme.findData(theme)
        self._theme.setCurrentIndex(max(idx, 0))
        self._hotkey_edit.setText(s.get("global_hotkey", "Ctrl+Shift+H"))
        self._hotkey_enabled.setChecked(s.get("global_hotkey_enabled", True))
        self._mini_widget_enabled.setChecked(s.get("mini_widget_enabled", False))
        wpos_idx = self._widget_position.findData(s.get("mini_widget_position", "bottom-right"))
        self._widget_position.setCurrentIndex(max(wpos_idx, 0))
        self._widget_offset_x.setValue(s.get("mini_widget_offset_x", 12))
        self._widget_offset_y.setValue(s.get("mini_widget_offset_y", 12))
        self._mini_overlay_enabled.setChecked(s.get("mini_overlay_enabled", False))
        pos_idx = self._overlay_position.findData(s.get("mini_overlay_position", "top-right"))
        self._overlay_position.setCurrentIndex(max(pos_idx, 0))
        self._overlay_hide_secs.setValue(s.get("mini_overlay_auto_hide_seconds", 8))

    def _save(self) -> None:
        s = self._ctx.settings

        # General
        new_model = self._model.currentText().strip()
        s.set("model", new_model)
        s.set("ollama_url", self._ollama_url.text().strip())
        s.set("log_level", self._log_level.currentText())
        start_with_windows = self._start_windows.isChecked()
        s.set("start_with_windows", start_with_windows)
        s.set("greet_on_startup", self._greet_startup.isChecked())
        s.set("chat_timestamps_enabled", self._chat_timestamps.isChecked())
        s.set("startup_delay_seconds", self._startup_delay.value())
        from app.core.startup import set_autostart
        set_autostart(start_with_windows)

        # Apply model switch immediately
        if self._ctx.model_manager:
            self._ctx.model_manager.switch(new_model)

        # Appearance
        new_theme = self._theme.currentData()
        s.set("theme", new_theme)
        from app.desktop.theme import set_theme
        set_theme(new_theme)
        s.set("global_hotkey", self._hotkey_edit.text().strip())
        s.set("global_hotkey_enabled", self._hotkey_enabled.isChecked())
        s.set("mini_widget_enabled", self._mini_widget_enabled.isChecked())
        s.set("mini_widget_position", self._widget_position.currentData())
        s.set("mini_widget_offset_x", self._widget_offset_x.value())
        s.set("mini_widget_offset_y", self._widget_offset_y.value())
        s.set("mini_overlay_enabled", self._mini_overlay_enabled.isChecked())
        s.set("mini_overlay_position", self._overlay_position.currentData())
        s.set("mini_overlay_auto_hide_seconds", self._overlay_hide_secs.value())

        self._ctx.logger.info("Settings saved.")
        self.close()

    def _refresh_models(self) -> None:
        if not self._ctx.model_manager:
            return
        models = self._ctx.model_manager.list_available()
        current = self._model.currentText()
        self._model.clear()
        if models:
            for m in models:
                self._model.addItem(m)
            idx = self._model.findText(current)
            if idx >= 0:
                self._model.setCurrentIndex(idx)
            else:
                self._model.setCurrentText(current)
        else:
            self._model.addItem(current)
            self._model.setCurrentText(current)

    def _do_memory_search(self) -> None:
        keyword = self._mem_search.text().strip()
        if not keyword or not self._ctx.store:
            return
        from PySide6.QtWidgets import QListWidgetItem
        self._mem_results.clear()

        memories = self._ctx.store.search_memories(keyword)
        for m in memories:
            tags = f" [{m.tags}]" if m.tags else ""
            item = QListWidgetItem(
                f"[Memory #{m.id}] {m.created_at[:10]}{tags}  {m.content}"
            )
            self._mem_results.addItem(item)

        from app.memory.search import search_notes, search_todos
        notes = search_notes(self._ctx.db, keyword)
        for n in notes:
            tags = f" [{n.get('tags', '')}]" if n.get("tags") else ""
            item = QListWidgetItem(
                f"[Note #{n['id']}] {n['created_at'][:10]}{tags}  {n['text']}"
            )
            self._mem_results.addItem(item)

        todos = search_todos(self._ctx.db, keyword)
        for t in todos:
            done = " ✓" if t.get("done") else ""
            item = QListWidgetItem(
                f"[Todo #{t['id']}]{done} {t['created_at'][:10]}  {t['text']}"
            )
            self._mem_results.addItem(item)

        if not self._mem_results.count():
            self._mem_results.addItem(f"No results for '{keyword}'.")

    def showEvent(self, event) -> None:
        self._load()
        super().showEvent(event)
