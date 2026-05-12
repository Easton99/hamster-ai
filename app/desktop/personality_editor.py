import json
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.desktop.icons import make_hamster_icon
from app.desktop.theme import ACCENT, TEXT_MUTED

if TYPE_CHECKING:
    from app.core.app_context import AppContext

DEFAULT_PROFILE_NAME = "Hamster"


class PersonalityEditor(QWidget):
    profile_changed = Signal(str)

    def __init__(self, ctx: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._profiles: dict = {}
        self._selected: str | None = None
        self._config_path = Path(ctx.base_dir) / "config" / "personality_profiles.json"
        self._load_profiles()
        self._setup_ui()
        self._refresh_list()

    def _load_profiles(self) -> None:
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._profiles = {p["name"]: p for p in data}
            elif isinstance(data, dict):
                self._profiles = {data["name"]: data}
        except Exception:
            self._profiles = {}
        if DEFAULT_PROFILE_NAME not in self._profiles:
            self._profiles[DEFAULT_PROFILE_NAME] = {
                "name": DEFAULT_PROFILE_NAME,
                "tone": "casual, brief, slightly cheeky",
                "greeting_style": "short",
                "example_phrases": ["Still grinding?", "Need a hand?", "Hamster online."],
            }

    def _save_profiles(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(list(self._profiles.values()), indent=2),
            encoding="utf-8",
        )

    def _setup_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # Left — list + buttons
        left = QVBoxLayout()
        left.setSpacing(6)

        lbl = QLabel("Profiles")
        lbl.setStyleSheet(f"font-weight: bold; color: {ACCENT}; background: transparent;")
        left.addWidget(lbl)

        self._list = QListWidget()
        self._list.setMaximumWidth(160)
        self._list.currentTextChanged.connect(self._on_select)
        left.addWidget(self._list)

        btn_new = QPushButton("New")
        btn_new.clicked.connect(self._new_profile)
        btn_del = QPushButton("Delete")
        btn_del.clicked.connect(self._delete_profile)
        btn_del.setStyleSheet("background: #C06060; color: white; border-radius: 6px; padding: 5px 10px;")
        left.addWidget(btn_new)
        left.addWidget(btn_del)

        # Right — edit form
        right = QVBoxLayout()
        right.setSpacing(6)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)

        self._name_edit = QLineEdit()
        self._name_edit.setReadOnly(True)
        form.addRow("Name:", self._name_edit)

        self._tone_edit = QLineEdit()
        self._tone_edit.setPlaceholderText("e.g. casual, brief, slightly cheeky")
        form.addRow("Tone:", self._tone_edit)

        right.addLayout(form)

        phrases_lbl = QLabel("Example phrases (one per line):")
        phrases_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
        right.addWidget(phrases_lbl)

        from PySide6.QtWidgets import QTextEdit
        self._phrases_edit = QTextEdit()
        self._phrases_edit.setMaximumHeight(100)
        self._phrases_edit.setPlaceholderText("One phrase per line")
        right.addWidget(self._phrases_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save Profile")
        save_btn.clicked.connect(self._save_current)
        use_btn = QPushButton("Use This Profile")
        use_btn.clicked.connect(self._use_profile)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(use_btn)
        right.addLayout(btn_row)
        right.addStretch()

        root.addLayout(left)
        root.addLayout(right)

    def _refresh_list(self) -> None:
        current = self._ctx.settings.get("personality", DEFAULT_PROFILE_NAME)
        self._list.clear()
        for name in self._profiles:
            item = QListWidgetItem(name)
            self._list.addItem(item)
            if name == current:
                self._list.setCurrentItem(item)
        if not self._list.currentItem() and self._list.count():
            self._list.setCurrentRow(0)

    def _on_select(self, name: str) -> None:
        self._selected = name
        profile = self._profiles.get(name, {})
        self._name_edit.setText(profile.get("name", name))
        self._tone_edit.setText(profile.get("tone", ""))
        phrases = profile.get("example_phrases", [])
        self._phrases_edit.setPlainText("\n".join(phrases))
        is_default = (name == DEFAULT_PROFILE_NAME)
        self._tone_edit.setReadOnly(is_default)

    def _save_current(self) -> None:
        if not self._selected:
            return
        profile = self._profiles.get(self._selected, {})
        if self._selected != DEFAULT_PROFILE_NAME:
            profile["tone"] = self._tone_edit.text().strip()
        phrases = [
            p.strip()
            for p in self._phrases_edit.toPlainText().splitlines()
            if p.strip()
        ]
        profile["example_phrases"] = phrases
        self._profiles[self._selected] = profile
        self._save_profiles()

    def _use_profile(self) -> None:
        if not self._selected:
            return
        self._save_current()
        self._ctx.settings.set("personality", self._selected)
        self.profile_changed.emit(self._selected)

    def _new_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self._profiles:
            QMessageBox.warning(self, "Name taken", f"A profile named '{name}' already exists.")
            return
        self._profiles[name] = {
            "name": name,
            "tone": "casual, helpful",
            "greeting_style": "short",
            "example_phrases": [],
        }
        self._save_profiles()
        self._refresh_list()
        items = self._list.findItems(name, Qt.MatchExactly)
        if items:
            self._list.setCurrentItem(items[0])

    def _delete_profile(self) -> None:
        if not self._selected or self._selected == DEFAULT_PROFILE_NAME:
            QMessageBox.information(self, "Cannot delete", "The default Hamster profile cannot be deleted.")
            return
        reply = QMessageBox.question(
            self, "Delete profile",
            f"Delete the '{self._selected}' profile?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            del self._profiles[self._selected]
            self._save_profiles()
            self._selected = None
            self._refresh_list()
