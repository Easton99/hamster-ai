from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.health_checks import FAIL, OK, WARNING
from app.desktop.icons import make_hamster_icon
from app.desktop.theme import ACCENT, BG, TEXT, TEXT_MUTED

if TYPE_CHECKING:
    from app.core.app_context import AppContext

_STATUS_COLORS = {OK: "#5B9B5B", WARNING: "#C08050", FAIL: "#BB4444"}
_STATUS_ICONS  = {OK: "✓", WARNING: "!", FAIL: "✗"}


class _HealthWorker(QThread):
    done = Signal(list)

    def __init__(self, app: "AppContext") -> None:
        super().__init__()
        self._app = app

    def run(self) -> None:
        from app.core.health_checks import run_all
        self.done.emit(run_all(self._app))


class DiagnosticsWindow(QWidget):
    def __init__(self, ctx: "AppContext", parent=None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._diag = ctx.diagnostics
        self._worker: _HealthWorker | None = None
        self._last_results = []

        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("Hamster AI — Diagnostics")
        self.setWindowIcon(make_hamster_icon())
        self.resize(560, 620)
        self.setMinimumSize(480, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Title + run button
        title_row = QHBoxLayout()
        title = QLabel("Diagnostics")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {ACCENT}; background: transparent;")
        self._run_btn = QPushButton("Run checks ▶")
        self._run_btn.setFixedWidth(120)
        self._run_btn.clicked.connect(self._run_checks)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self._run_btn)
        root.addLayout(title_row)

        # ── Health checks table ───────────────────────────────────────────────
        hc_group = QGroupBox("Health Checks")
        hc_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {TEXT}; border: 1px solid #D4C4B0; border-radius: 6px; margin-top: 6px; padding-top: 8px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 8px; }}")
        hc_layout = QVBoxLayout(hc_group)
        hc_layout.setContentsMargins(8, 8, 8, 8)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["", "Check", "Result"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setShowGrid(False)
        self._table.setColumnWidth(0, 24)
        self._table.setColumnWidth(1, 160)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            f"QTableWidget {{ background: {BG}; border: none; color: {TEXT}; }}"
            f"QTableWidget::item {{ padding: 4px; }}"
            f"QHeaderView::section {{ background: transparent; color: {TEXT_MUTED}; border: none; font-size: 11px; padding: 4px; }}"
        )
        self._table.setFixedHeight(200)
        hc_layout.addWidget(self._table)
        root.addWidget(hc_group)

        # ── Fix suggestions ───────────────────────────────────────────────────
        self._fix_group = QGroupBox("Fix Suggestions")
        self._fix_group.setStyleSheet(hc_group.styleSheet())
        self._fix_layout = QVBoxLayout(self._fix_group)
        self._fix_layout.setContentsMargins(8, 8, 8, 8)
        self._no_fixes_label = QLabel("No issues found.")
        self._no_fixes_label.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
        self._fix_layout.addWidget(self._no_fixes_label)
        root.addWidget(self._fix_group)

        # ── Recent errors (current session) ───────────────────────────────────
        err_group = QGroupBox("Recent Errors & Warnings — This Session")
        err_group.setStyleSheet(hc_group.styleSheet())
        err_layout = QVBoxLayout(err_group)
        err_layout.setContentsMargins(8, 8, 8, 8)

        _err_style = (
            f"QTextEdit {{ background: {BG}; border: none; color: {TEXT};"
            f" font-family: Consolas, monospace; font-size: 11px; }}"
        )

        self._errors_text = QTextEdit()
        self._errors_text.setReadOnly(True)
        self._errors_text.setFixedHeight(120)
        self._errors_text.setStyleSheet(_err_style)
        err_layout.addWidget(self._errors_text)

        # Collapsible older-session section
        self._older_toggle = QPushButton("▶  Show older sessions")
        self._older_toggle.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {TEXT_MUTED};"
            f" font-size: 11px; text-align: left; padding: 2px 0px; }}"
            f"QPushButton:hover {{ color: {ACCENT}; }}"
        )
        self._older_toggle.setCursor(Qt.PointingHandCursor)
        self._older_toggle.clicked.connect(self._toggle_older)
        err_layout.addWidget(self._older_toggle)

        self._older_text = QTextEdit()
        self._older_text.setReadOnly(True)
        self._older_text.setFixedHeight(100)
        self._older_text.setStyleSheet(_err_style)
        self._older_text.hide()
        err_layout.addWidget(self._older_text)

        root.addWidget(err_group)

        root.addStretch()

        # ── Bottom buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        export_btn = QPushButton("Export Bundle")
        export_btn.clicked.connect(self._export_bundle)
        clear_btn = QPushButton("Clear Logs")
        clear_btn.setStyleSheet("background: #C4A882; color: white; font-weight: bold; border-radius: 6px; padding: 6px 16px;")
        clear_btn.clicked.connect(self._clear_logs)
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background: #C4A882; color: white; font-weight: bold; border-radius: 6px; padding: 6px 16px;")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(export_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    # ── Health check runner ───────────────────────────────────────────────────

    def _run_checks(self) -> None:
        self._run_btn.setEnabled(False)
        self._run_btn.setText("Running…")
        self._table.setRowCount(0)
        self._worker = _HealthWorker(self._ctx)
        self._worker.done.connect(self._on_checks_done)
        self._worker.start()

    def _on_checks_done(self, results: list) -> None:
        self._last_results = results
        self._table.setRowCount(len(results))

        for row, r in enumerate(results):
            color = _STATUS_COLORS.get(r.status, TEXT)
            icon_item = QTableWidgetItem(_STATUS_ICONS.get(r.status, "?"))
            icon_item.setForeground(QColor(color))
            icon_item.setFont(QFont("Segoe UI", 11, QFont.Bold))
            icon_item.setTextAlignment(Qt.AlignCenter)

            name_item = QTableWidgetItem(r.name)
            name_item.setForeground(QColor(TEXT))

            msg_item = QTableWidgetItem(r.message)
            msg_item.setForeground(QColor(color))

            self._table.setItem(row, 0, icon_item)
            self._table.setItem(row, 1, name_item)
            self._table.setItem(row, 2, msg_item)
            self._table.setRowHeight(row, 28)

        self._refresh_fixes(results)
        self._refresh_errors()

        self._run_btn.setEnabled(True)
        self._run_btn.setText("Run checks ▶")

    def _refresh_fixes(self, results: list) -> None:
        # Clear existing fix widgets (keep the no_fixes_label)
        while self._fix_layout.count():
            item = self._fix_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        suggestions = self._ctx.diagnostics.suggestions_for(results)
        if not suggestions:
            lbl = QLabel("No issues found.")
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; background: transparent;")
            self._fix_layout.addWidget(lbl)
            return

        for fix in suggestions:
            row = QHBoxLayout()
            desc = QLabel(f"<b>{fix.label}</b> — {fix.description}")
            desc.setWordWrap(True)
            desc.setStyleSheet(f"background: transparent; color: {TEXT};")
            apply_btn = QPushButton("Apply")
            apply_btn.setFixedWidth(70)
            apply_btn.clicked.connect(lambda checked, fk=fix.key: self._apply_fix(fk))
            row.addWidget(desc)
            row.addWidget(apply_btn)
            container = QWidget()
            container.setLayout(row)
            container.setStyleSheet("background: transparent;")
            self._fix_layout.addWidget(container)

    def _refresh_errors(self) -> None:
        current, older = self._ctx.diagnostics.recent_errors_split()
        self._errors_text.setPlainText(
            "\n".join(current) if current else "No errors or warnings this session."
        )
        self._older_text.setPlainText(
            "\n".join(older) if older else "No older errors or warnings."
        )
        self._older_toggle.setVisible(bool(older))

    def _toggle_older(self) -> None:
        visible = self._older_text.isVisible()
        self._older_text.setVisible(not visible)
        self._older_toggle.setText(
            "▼  Hide older sessions" if not visible else "▶  Show older sessions"
        )

    def _apply_fix(self, fix_key: str) -> None:
        fix_labels = {s.key: s.label for s in self._ctx.diagnostics.suggestions_for(self._last_results)}
        label = fix_labels.get(fix_key, fix_key)

        reply = QMessageBox.question(
            self, "Apply Fix",
            f"Apply fix: {label}?\n\nThis will make changes to your system.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ok, msg = self._ctx.diagnostics.apply_fix(fix_key)
        if ok:
            QMessageBox.information(self, "Fix Applied", msg)
        else:
            QMessageBox.warning(self, "Fix Failed", msg)

        self._run_checks()

    # ── Button actions ────────────────────────────────────────────────────────

    def _export_bundle(self) -> None:
        from pathlib import Path
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Diagnostic Bundle",
            str(self._ctx.data_dir / "hamster_diagnostics.zip"),
            "ZIP files (*.zip)",
        )
        if not dest:
            return
        try:
            path = self._ctx.diagnostics.export_bundle(Path(dest).parent)
            import shutil
            shutil.move(str(path), dest)
            QMessageBox.information(self, "Exported", f"Bundle saved to:\n{dest}")
        except Exception as exc:
            QMessageBox.warning(self, "Export Failed", str(exc))

    def _clear_logs(self) -> None:
        reply = QMessageBox.question(
            self, "Clear Logs",
            "Delete all log files? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._ctx.diagnostics.clear_logs()
            self._errors_text.setPlainText("Logs cleared.")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._run_checks()
