from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.desktop.icons import make_hamster_icon
from app.desktop.theme import ACCENT, BG, TEXT, TEXT_MUTED

if TYPE_CHECKING:
    from app.core.app_context import AppContext


# ── Per-plugin config dialog ──────────────────────────────────────────────────

class _PluginConfigDialog(QDialog):
    def __init__(self, plugin_name: str, schema: list, ctx, parent=None) -> None:
        super().__init__(parent)
        self._plugin_name = plugin_name
        self._schema = schema
        self._ctx = ctx
        self._widgets: dict = {}
        self.setWindowTitle(f"{plugin_name} — Settings")
        self.setMinimumWidth(360)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)

        for field in self._schema:
            key = field["key"]
            label = field.get("label", key)
            ftype = field.get("type", "text")
            default = field.get("default")

            if ftype == "toggle":
                w = QCheckBox()
                w.setChecked(bool(default))
            elif ftype == "number":
                w = QSpinBox()
                w.setRange(0, 99999)
                w.setValue(int(default) if default is not None else 0)
            elif ftype == "slider":
                w = QDoubleSpinBox()
                w.setRange(field.get("min", 0), field.get("max", 100))
                w.setValue(float(default) if default is not None else 0)
                w.setSingleStep(0.1)
            else:
                w = QLineEdit()
                w.setText(str(default) if default is not None else "")

            self._widgets[key] = (w, ftype)
            form.addRow(f"{label}:", w)

        root.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load_values(self) -> None:
        key_prefix = f"plugin.{self._plugin_name}."
        for field in self._schema:
            key = field["key"]
            stored = self._ctx.settings.get(key_prefix + key)
            if stored is None:
                continue
            w, ftype = self._widgets[key]
            if ftype == "toggle":
                w.setChecked(bool(stored))
            elif ftype in ("number", "slider"):
                w.setValue(stored)
            else:
                w.setText(str(stored))

    def _save(self) -> None:
        key_prefix = f"plugin.{self._plugin_name}."
        for field in self._schema:
            key = field["key"]
            w, ftype = self._widgets[key]
            if ftype == "toggle":
                val = w.isChecked()
            elif ftype in ("number", "slider"):
                val = w.value()
            else:
                val = w.text()
            self._ctx.settings.set(key_prefix + key, val)
        self.accept()


# ── Toggle switch widget ──────────────────────────────────────────────────────

class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    _W  = 46
    _H  = 26
    _KD = 20   # knob diameter

    def __init__(self, checked: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.PointingHandCursor)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, value: bool) -> None:
        if self._checked != value:
            self._checked = value
            self.update()

    def mousePressEvent(self, event) -> None:
        self._checked = not self._checked
        self.update()
        self.toggled.emit(self._checked)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        track_h  = self._H - 6
        track_y  = 3
        radius   = track_h // 2

        # Track
        track_color = QColor(ACCENT) if self._checked else QColor("#C4B8AA")
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, track_y, self._W, track_h, radius, radius)

        # Knob
        knob_x = self._W - self._KD - 3 if self._checked else 3
        knob_y = (self._H - self._KD) // 2
        p.setBrush(QBrush(QColor("white")))
        p.setPen(QPen(QColor(0, 0, 0, 30), 1))
        p.drawEllipse(knob_x, knob_y, self._KD, self._KD)

        p.end()


# ── Plugin card ───────────────────────────────────────────────────────────────

class PluginCard(QFrame):
    def __init__(self, info: dict, plugin_manager, ctx, parent=None) -> None:
        super().__init__(parent)
        self._pm   = plugin_manager
        self._ctx  = ctx
        self._name = info["name"]

        self.setObjectName("PluginCard")
        self.setStyleSheet(
            "QFrame#PluginCard {"
            f"  background: #F5EDE3;"
            f"  border: 1px solid #D4C0A8;"
            f"  border-radius: 10px;"
            "}"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        name_lbl = QLabel(info["name"])
        name_lbl.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {TEXT}; background: transparent;"
        )

        text_col.addWidget(name_lbl)

        if info.get("description"):
            desc_lbl = QLabel(info["description"])
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                f"font-size: 11px; color: {TEXT_MUTED}; background: transparent;"
            )
            text_col.addWidget(desc_lbl)

        layout.addLayout(text_col, stretch=1)

        # Configure button (only if plugin has settings)
        if self._has_settings(info["name"]):
            cfg_btn = QPushButton("Configure")
            cfg_btn.setFixedHeight(26)
            cfg_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {ACCENT};"
                f" border: 1px solid {ACCENT}; border-radius: 6px;"
                f" padding: 2px 10px; font-size: 11px; font-weight: normal; }}"
                f"QPushButton:hover {{ background: #F2E0C8; }}"
            )
            cfg_btn.clicked.connect(lambda: self._open_config())
            layout.addWidget(cfg_btn)

        # Toggle
        self._toggle = ToggleSwitch(checked=info["enabled"])
        self._toggle.toggled.connect(self._on_toggle)
        layout.addWidget(self._toggle)

    def refresh(self, enabled: bool) -> None:
        self._toggle.set_checked(enabled)

    def _on_toggle(self, checked: bool) -> None:
        if checked:
            self._pm.enable_plugin(self._name)
        else:
            self._pm.disable_plugin(self._name)

    def _has_settings(self, plugin_name: str) -> bool:
        import json
        from pathlib import Path
        cfg = Path(self._ctx.plugins_dir) / plugin_name / "config.json"
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            return bool(data.get("settings"))
        except Exception:
            return False

    def _open_config(self) -> None:
        import json
        from pathlib import Path
        cfg_path = Path(self._ctx.plugins_dir) / self._name / "config.json"
        try:
            schema = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return
        settings_schema = schema.get("settings", [])
        if not settings_schema:
            return
        dlg = _PluginConfigDialog(self._name, settings_schema, self._ctx, self)
        dlg.exec()


# ── Plugins window ────────────────────────────────────────────────────────────

class PluginsWindow(QWidget):
    def __init__(self, ctx: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._ctx   = ctx
        self._cards: dict[str, PluginCard] = {}
        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("Hamster AI — Plugins")
        self.setWindowIcon(make_hamster_icon())
        self.setFixedWidth(420)
        self.setMinimumHeight(200)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)

        heading = QLabel("Plugins")
        heading.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {ACCENT}; background: transparent;"
        )
        root.addWidget(heading)

        hint = QLabel("Changes take effect immediately.")
        hint.setStyleSheet(
            f"font-size: 11px; color: {TEXT_MUTED}; background: transparent;"
        )
        root.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._cards_layout = QVBoxLayout(self._content)
        self._cards_layout.setSpacing(8)
        self._cards_layout.setContentsMargins(0, 4, 0, 4)

        self._rebuild()

        scroll.setWidget(self._content)
        root.addWidget(scroll)

    def _rebuild(self) -> None:
        # Clear
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        pm = self._ctx.plugin_manager
        plugins = pm.list_plugins() if pm else []

        if not plugins:
            lbl = QLabel("No plugins installed.")
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
            self._cards_layout.addWidget(lbl)
        else:
            for info in plugins:
                card = PluginCard(info, pm, self._ctx)
                self._cards[info["name"]] = card
                self._cards_layout.addWidget(card)

        self._cards_layout.addStretch()

    def showEvent(self, event) -> None:
        # Refresh toggle states each time window opens
        pm = self._ctx.plugin_manager
        if pm:
            for info in pm.list_plugins():
                card = self._cards.get(info["name"])
                if card:
                    card.refresh(info["enabled"])
                else:
                    self._rebuild()
                    break
        super().showEvent(event)
