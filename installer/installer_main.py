"""Hamster AI Installer — PySide6 QWizard (Install / Modify / Remove)."""
import subprocess
import sys
import winreg
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWizard, QWizardPage,
)

# ── Theme ──────────────────────────────────────────────────────────────────
_T = {
    "BG":      "#FAF7F2",
    "PRIMARY": "#F5E6D3",
    "ACCENT":  "#A67C52",
    "SEC":     "#F2B880",
    "TEXT":    "#3E2C1C",
    "MUTED":   "#8B6A4A",
    "SURFACE": "#F5EDE3",
    "BORDER":  "#D4C0A8",
}

STYLESHEET = f"""
QWidget {{
    background-color: {_T['BG']};
    color: {_T['TEXT']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
QWizard, QWizardPage {{
    background-color: {_T['BG']};
}}
QPushButton {{
    background-color: {_T['ACCENT']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 18px;
    font-weight: bold;
}}
QPushButton:hover  {{ background-color: #8B6A42; }}
QPushButton:pressed {{ background-color: #7A5A38; }}
QPushButton:disabled {{ background-color: #C4A882; color: #F0E4D4; }}
QPushButton#flat {{
    background: transparent;
    color: {_T['ACCENT']};
    font-weight: normal;
    padding: 4px 8px;
}}
QPushButton#flat:hover {{ background: {_T['PRIMARY']}; }}
QLabel {{ background: transparent; }}
QLabel#title {{
    font-size: 20px;
    font-weight: bold;
    color: {_T['TEXT']};
}}
QLabel#subtitle {{
    font-size: 13px;
    color: {_T['MUTED']};
}}
QLabel#section {{
    font-size: 12px;
    font-weight: bold;
    color: {_T['ACCENT']};
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QLabel#pass {{ color: #5A8A5A; font-weight: bold; }}
QLabel#fail {{ color: #AA4444; font-weight: bold; }}
QLabel#warn {{ color: #AA7700; font-weight: bold; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1.5px solid {_T['ACCENT']};
    background: white;
}}
QCheckBox::indicator:checked {{
    background-color: {_T['ACCENT']};
}}
QLineEdit {{
    background: white;
    border: 1.5px solid {_T['SEC']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {_T['TEXT']};
}}
QLineEdit:focus {{ border-color: {_T['ACCENT']}; }}
QProgressBar {{
    background: {_T['PRIMARY']};
    border: 1px solid {_T['BORDER']};
    border-radius: 6px;
    height: 14px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {_T['ACCENT']};
    border-radius: 6px;
}}
QFrame#card {{
    background: {_T['SURFACE']};
    border: 1px solid {_T['BORDER']};
    border-radius: 10px;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {_T['PRIMARY']}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {_T['SEC']}; border-radius: 4px; min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

# ── Registry helpers ───────────────────────────────────────────────────────
_REG_KEY = r"Software\HamsterAI"


def _reg_read(name: str, default=None):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY) as k:
            val, _ = winreg.QueryValueEx(k, name)
            return val
    except OSError:
        return default


def _reg_write(name: str, value: str) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_KEY) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)


def _reg_delete() -> None:
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, _REG_KEY)
    except OSError:
        pass


# ── Startup registry helpers ───────────────────────────────────────────────
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_NAME = "HamsterAI"


def _startup_set(pythonw: str, main_py: str) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _RUN_KEY, access=winreg.KEY_SET_VALUE
    ) as k:
        winreg.SetValueEx(k, _RUN_NAME, 0, winreg.REG_SZ, f'"{pythonw}" "{main_py}"')


def _startup_remove() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, access=winreg.KEY_SET_VALUE
        ) as k:
            winreg.DeleteValue(k, _RUN_NAME)
    except OSError:
        pass


def _startup_exists() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _RUN_NAME)
            return True
    except OSError:
        return False


# ── Icon ───────────────────────────────────────────────────────────────────
def _make_hamster_pixmap(size: int = 64) -> QPixmap:
    px = QPixmap(64, 64)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)

    p.setBrush(QBrush(QColor("#F5E6D3")))
    p.setPen(QPen(QColor("#A67C52"), 2))
    p.drawEllipse(6, 2, 20, 20)
    p.drawEllipse(38, 2, 20, 20)

    p.drawEllipse(8, 14, 48, 44)

    p.setBrush(QBrush(QColor("#F2B880")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(4, 34, 18, 14)
    p.drawEllipse(42, 34, 18, 14)

    p.setBrush(QBrush(QColor("#A67C52")))
    p.drawEllipse(26, 40, 12, 8)

    p.end()
    if size != 64:
        px = px.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return px


def _hamster_icon() -> QIcon:
    return QIcon(_make_hamster_pixmap(64))


# ── Plugin catalogue ───────────────────────────────────────────────────────
PLUGINS = [
    {
        "key":   "session_awareness",
        "label": "Session Awareness",
        "desc":  "Detects what you're doing — coding, gaming, browsing.",
        "default": True,
        "deps":  [],
    },
    {
        "key":   "insights",
        "label": "Insights",
        "desc":  "End-of-day and weekly activity summaries.",
        "default": True,
        "deps":  [],
    },
    {
        "key":   "scheduled_reminders",
        "label": "Scheduled Reminders",
        "desc":  "Time-based reminders via natural language.",
        "default": True,
        "deps":  [],
    },
    {
        "key":   "process_awareness",
        "label": "Process Awareness",
        "desc":  "Running processes, internet-using apps, and startup programs.",
        "default": False,
        "deps":  [],
    },
    {
        "key":   "audio_awareness",
        "label": "Audio Awareness",
        "desc":  "Detects whether audio is playing before interrupting you.",
        "default": False,
        "deps":  ["pycaw"],
    },
    {
        "key":   "voice_output",
        "label": "Voice Output",
        "desc":  "Speaks replies using Windows SAPI (local TTS).",
        "default": False,
        "deps":  ["pyttsx3"],
    },
    {
        "key":   "extended_system_stats",
        "label": "Extended System Stats",
        "desc":  "GPU, per-process CPU/RAM, disk usage, and network bandwidth.",
        "default": False,
        "deps":  ["GPUtil", "pywin32", "wmi"],
    },
    {
        "key":   "hardware_awareness",
        "label": "Hardware Awareness",
        "desc":  "Monitors, USB devices, battery status, and internet connectivity.",
        "default": False,
        "deps":  ["pywin32", "wmi"],
    },
]

# ── Install worker ─────────────────────────────────────────────────────────

class InstallWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, install_dir: Path, selected_keys: list[str],
                 start_with_windows: bool, create_shortcut: bool):
        super().__init__()
        self._dir = install_dir
        self._keys = selected_keys
        self._startup = start_with_windows
        self._shortcut = create_shortcut

    def run(self) -> None:
        try:
            steps = self._build_steps()
            total = len(steps)
            for i, (label, fn) in enumerate(steps):
                self.progress.emit(int(i / total * 100), label)
                fn()
            self.progress.emit(100, "Done.")
            self.finished.emit(True, "")
        except Exception as exc:
            self.finished.emit(False, str(exc))

    def _build_steps(self):
        steps = []

        # pip install core deps
        steps.append(("Installing core dependencies…", self._install_core))

        # pip install optional deps for selected plugins
        needed = set()
        for p in PLUGINS:
            if p["key"] in self._keys:
                needed.update(p["deps"])
        if needed:
            steps.append((
                f"Installing plugin dependencies: {', '.join(sorted(needed))}…",
                lambda pkgs=needed: self._pip_install(list(pkgs)),
            ))

        # data dir
        steps.append(("Creating data directories…", self._make_dirs))

        # startup
        if self._startup:
            steps.append(("Registering startup entry…", self._register_startup))
        else:
            steps.append(("Removing startup entry (if any)…", _startup_remove))

        # shortcut
        if self._shortcut:
            steps.append(("Creating desktop shortcut…", self._create_shortcut))

        # registry
        steps.append(("Saving installation record…", self._write_registry))

        return steps

    def _install_core(self) -> None:
        self._pip_install(["PySide6", "psutil"])

    def _pip_install(self, pkgs: list[str]) -> None:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", *pkgs],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _make_dirs(self) -> None:
        for sub in ("data/logs", "data/config", "config"):
            (self._dir / sub).mkdir(parents=True, exist_ok=True)

    def _register_startup(self) -> None:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.exists():
            pythonw = Path(sys.executable)
        main_py = self._dir / "app" / "main.py"
        _startup_set(str(pythonw), str(main_py))

    def _create_shortcut(self) -> None:
        desktop = Path.home() / "Desktop"
        target_py = self._dir / "app" / "main.py"
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.exists():
            pythonw = Path(sys.executable)
        vbs = desktop / "HamsterAI.vbs"
        vbs.write_text(
            f'Set WshShell = CreateObject("WScript.Shell")\n'
            f'WshShell.Run Chr(34) & "{pythonw}" & Chr(34) & " " & '
            f'Chr(34) & "{target_py}" & Chr(34), 0\n',
            encoding="utf-8",
        )

    def _write_registry(self) -> None:
        _reg_write("InstallPath", str(self._dir))
        _reg_write("SelectedPlugins", ",".join(self._keys))
        _reg_write("Version", "1.0.0")


# ── Shared helpers ─────────────────────────────────────────────────────────

def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet(f"background: {_T['BORDER']}; border: none; max-height: 1px;")
    return line


def _check_ollama() -> tuple[bool, str]:
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            return r.status == 200, "Running"
    except Exception:
        return False, "Not detected"


def _check_python() -> tuple[bool, str]:
    ok = sys.version_info >= (3, 11)
    ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return ok, ver


# ══════════════════════════════════════════════════════════════════════════════
# Pages
# ══════════════════════════════════════════════════════════════════════════════

class WelcomePage(QWizardPage):
    def __init__(self, mode: str = "install"):
        super().__init__()
        self.setTitle("")
        self._mode = mode
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(40, 40, 40, 40)

        # header card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        card_layout.setContentsMargins(32, 32, 32, 32)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(_make_hamster_pixmap(72))
        icon_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_lbl)

        title = QLabel("Hamster AI")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        f = title.font()
        f.setPointSize(22)
        f.setBold(True)
        title.setFont(f)
        card_layout.addWidget(title)

        if self._mode == "install":
            sub_text = "A local-first Windows desktop AI companion.\nRuns fully offline. No cloud. No subscriptions."
        else:
            sub_text = "Modify your installation or remove Hamster AI."

        sub = QLabel(sub_text)
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        card_layout.addWidget(sub)

        root.addWidget(card)
        root.addStretch()

        if self._mode == "install":
            note = QLabel("Click <b>Next</b> to check prerequisites and choose your setup.")
            note.setObjectName("subtitle")
            note.setAlignment(Qt.AlignCenter)
            note.setWordWrap(True)
            root.addWidget(note)


class PrerequisitesPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Prerequisites")
        self.setSubTitle("Checking your system before installation.")
        self._rows: dict[str, QLabel] = {}
        self._complete = False
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setSpacing(12)
        cl.setContentsMargins(24, 20, 24, 20)

        for key, label in [
            ("python", "Python 3.11+"),
            ("ollama", "Ollama (localhost:11434)"),
        ]:
            row = QHBoxLayout()
            name_lbl = QLabel(label)
            status = QLabel("Checking…")
            status.setObjectName("warn")
            self._rows[key] = status
            row.addWidget(name_lbl)
            row.addStretch()
            row.addWidget(status)
            cl.addWidget(_divider() if key != "python" else QLabel())
            cl.addLayout(row)

        root.addWidget(card)

        note = QLabel(
            "Ollama must be installed and running before Hamster AI can work.\n"
            "Download from <b>ollama.com</b> and run <code>ollama serve</code>."
        )
        note.setObjectName("subtitle")
        note.setWordWrap(True)
        root.addWidget(note)

        recheck = QPushButton("Check Again")
        recheck.setFixedWidth(120)
        recheck.clicked.connect(self._run_checks)
        root.addWidget(recheck, alignment=Qt.AlignLeft)

        root.addStretch()

    def initializePage(self) -> None:
        self._run_checks()

    def _run_checks(self) -> None:
        py_ok, py_ver = _check_python()
        ol_ok, ol_msg = _check_ollama()

        lbl = self._rows["python"]
        lbl.setText(f"✓  {py_ver}" if py_ok else f"✗  {py_ver} (need 3.11+)")
        lbl.setObjectName("pass" if py_ok else "fail")
        lbl.setStyle(lbl.style())

        lbl2 = self._rows["ollama"]
        lbl2.setText(f"✓  {ol_msg}" if ol_ok else f"⚠  {ol_msg}")
        lbl2.setObjectName("pass" if ol_ok else "warn")
        lbl2.setStyle(lbl2.style())

        self._complete = py_ok
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._complete


class PluginPage(QWizardPage):
    def __init__(self, preselected: list[str] | None = None):
        super().__init__()
        self.setTitle("Choose Plugins")
        self.setSubTitle("Select the optional features you want. Core features are always included.")
        self._pre = preselected
        self._checks: dict[str, QCheckBox] = {}
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(24, 16, 24, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        il = QVBoxLayout(inner)
        il.setSpacing(8)
        il.setContentsMargins(0, 0, 8, 0)

        for p in PLUGINS:
            card = QFrame()
            card.setObjectName("card")
            cl = QHBoxLayout(card)
            cl.setContentsMargins(16, 12, 16, 12)
            cl.setSpacing(12)

            cb = QCheckBox()
            cb.setChecked(
                (self._pre is not None and p["key"] in self._pre)
                or (self._pre is None and p["default"])
            )
            self._checks[p["key"]] = cb
            cl.addWidget(cb, alignment=Qt.AlignTop)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)

            name = QLabel(f"<b>{p['label']}</b>")
            name.setStyleSheet("background: transparent;")
            text_col.addWidget(name)

            desc = QLabel(p["desc"])
            desc.setObjectName("subtitle")
            desc.setWordWrap(True)
            text_col.addWidget(desc)

            if p["deps"]:
                deps_lbl = QLabel(f"Extra packages: {', '.join(p['deps'])}")
                deps_lbl.setStyleSheet(f"color: {_T['MUTED']}; font-size: 11px; background: transparent;")
                text_col.addWidget(deps_lbl)

            cl.addLayout(text_col)
            il.addWidget(card)

        il.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

    def selected_keys(self) -> list[str]:
        return [k for k, cb in self._checks.items() if cb.isChecked()]


class OptionsPage(QWizardPage):
    def __init__(self, install_dir: Path):
        super().__init__()
        self.setTitle("Setup Options")
        self.setSubTitle("Configure how Hamster AI is set up on your PC.")
        self._install_dir = install_dir
        self._startup_cb: QCheckBox | None = None
        self._shortcut_cb: QCheckBox | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # install location (display only)
        loc_card = QFrame()
        loc_card.setObjectName("card")
        lc = QVBoxLayout(loc_card)
        lc.setContentsMargins(20, 14, 20, 14)
        lc.setSpacing(6)
        loc_hdr = QLabel("Installation folder")
        loc_hdr.setObjectName("section")
        lc.addWidget(loc_hdr)
        loc_path = QLineEdit(str(self._install_dir))
        loc_path.setReadOnly(True)
        lc.addWidget(loc_path)
        root.addWidget(loc_card)

        # options card
        opt_card = QFrame()
        opt_card.setObjectName("card")
        oc = QVBoxLayout(opt_card)
        oc.setContentsMargins(20, 14, 20, 14)
        oc.setSpacing(12)

        opt_hdr = QLabel("Options")
        opt_hdr.setObjectName("section")
        oc.addWidget(opt_hdr)

        self._startup_cb = QCheckBox("Start Hamster AI automatically with Windows")
        self._startup_cb.setChecked(_startup_exists())
        oc.addWidget(self._startup_cb)

        self._shortcut_cb = QCheckBox("Create a shortcut on the Desktop")
        self._shortcut_cb.setChecked(True)
        oc.addWidget(self._shortcut_cb)

        root.addWidget(opt_card)
        root.addStretch()

    def start_with_windows(self) -> bool:
        return self._startup_cb.isChecked() if self._startup_cb else False

    def create_shortcut(self) -> bool:
        return self._shortcut_cb.isChecked() if self._shortcut_cb else False


class InstallingPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installing")
        self.setSubTitle("Please wait while Hamster AI is set up.")
        self._done = False
        self._error = ""
        self._bar: QProgressBar | None = None
        self._status: QLabel | None = None
        self._worker: InstallWorker | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        icon = QLabel()
        icon.setPixmap(_make_hamster_pixmap(48))
        icon.setAlignment(Qt.AlignCenter)
        root.addWidget(icon)

        self._status = QLabel("Preparing…")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setObjectName("subtitle")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        root.addWidget(self._bar)

        root.addStretch()

    def initializePage(self) -> None:
        wiz = self.wizard()
        plugin_page: PluginPage = wiz.plugin_page
        options_page: OptionsPage = wiz.options_page

        self._worker = InstallWorker(
            install_dir=wiz.install_dir,
            selected_keys=plugin_page.selected_keys(),
            start_with_windows=options_page.start_with_windows(),
            create_shortcut=options_page.create_shortcut(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, pct: int, msg: str) -> None:
        self._bar.setValue(pct)
        self._status.setText(msg)

    def _on_finished(self, ok: bool, err: str) -> None:
        self._done = True
        self._error = err
        if ok:
            self._status.setText("Installation complete!")
            self._bar.setValue(100)
        else:
            self._status.setText(f"Error: {err}")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._done

    def had_error(self) -> bool:
        return bool(self._error)


class FinishPage(QWizardPage):
    def __init__(self, install_dir: Path):
        super().__init__()
        self.setTitle("All Done!")
        self._install_dir = install_dir
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(20)
        root.setContentsMargins(40, 40, 40, 40)

        icon = QLabel()
        icon.setPixmap(_make_hamster_pixmap(72))
        icon.setAlignment(Qt.AlignCenter)
        root.addWidget(icon)

        msg = QLabel(
            "<b>Hamster AI is ready.</b><br><br>"
            "Click <b>Finish</b> to close the installer.<br>"
            "Launch Hamster AI from the Desktop shortcut or run:<br>"
            f"<code>python app/main.py</code>"
        )
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        root.addWidget(msg)

        launch_btn = QPushButton("Launch Hamster AI Now")
        launch_btn.setFixedWidth(220)
        launch_btn.clicked.connect(self._launch)
        root.addWidget(launch_btn, alignment=Qt.AlignCenter)

        root.addStretch()

    def _launch(self) -> None:
        main_py = self._install_dir / "app" / "main.py"
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if not pythonw.exists():
            pythonw = Path(sys.executable)
        subprocess.Popen([str(pythonw), str(main_py)],
                         cwd=str(self._install_dir),
                         creationflags=subprocess.DETACHED_PROCESS)


# ══════════════════════════════════════════════════════════════════════════════
# Wizard
# ══════════════════════════════════════════════════════════════════════════════

class HamsterWizard(QWizard):
    PAGE_WELCOME      = 0
    PAGE_PREREQS      = 1
    PAGE_PLUGINS      = 2
    PAGE_OPTIONS      = 3
    PAGE_INSTALLING   = 4
    PAGE_FINISH       = 5

    def __init__(self, install_dir: Path, preselected: list[str] | None = None,
                 mode: str = "install"):
        super().__init__()
        self.install_dir = install_dir
        self.setWindowTitle("Hamster AI Setup")
        self.setWindowIcon(_hamster_icon())
        self.setWizardStyle(QWizard.ModernStyle)
        self.setFixedSize(620, 520)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.NoCancelButtonOnLastPage, True)

        self.setButtonText(QWizard.NextButton, "Next  →")
        self.setButtonText(QWizard.BackButton, "←  Back")
        self.setButtonText(QWizard.FinishButton, "Finish")
        self.setButtonText(QWizard.CancelButton, "Cancel")

        self.plugin_page  = PluginPage(preselected)
        self.options_page = OptionsPage(install_dir)
        installing_page   = InstallingPage()
        finish_page       = FinishPage(install_dir)

        self.setPage(self.PAGE_WELCOME,    WelcomePage(mode))
        self.setPage(self.PAGE_PREREQS,    PrerequisitesPage())
        self.setPage(self.PAGE_PLUGINS,    self.plugin_page)
        self.setPage(self.PAGE_OPTIONS,    self.options_page)
        self.setPage(self.PAGE_INSTALLING, installing_page)
        self.setPage(self.PAGE_FINISH,     finish_page)

        self.setStartId(self.PAGE_WELCOME)

        # Style the sidebar banner
        banner = QPixmap(160, 520)
        banner.fill(QColor(_T["PRIMARY"]))
        p = QPainter(banner)
        p.drawPixmap(44, 40, _make_hamster_pixmap(72))
        p.setPen(QColor(_T["ACCENT"]))
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(0, 130, 160, 30, Qt.AlignCenter, "Hamster AI")
        p.end()
        self.setPixmap(QWizard.BannerPixmap, banner)
        self.setPixmap(QWizard.WatermarkPixmap, banner)


# ══════════════════════════════════════════════════════════════════════════════
# Modify / Remove dialog
# ══════════════════════════════════════════════════════════════════════════════

class ModeDialog(QDialog):
    def __init__(self, install_path: str):
        super().__init__()
        self.setWindowTitle("Hamster AI — Maintenance")
        self.setWindowIcon(_hamster_icon())
        self.setFixedSize(420, 280)
        self._choice = None
        self._build(install_path)

    def _build(self, install_path: str) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(32, 32, 32, 32)

        icon = QLabel()
        icon.setPixmap(_make_hamster_pixmap(48))
        icon.setAlignment(Qt.AlignCenter)
        root.addWidget(icon)

        title = QLabel("<b>Hamster AI is already installed.</b>")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        path_lbl = QLabel(f"<small>{install_path}</small>")
        path_lbl.setObjectName("subtitle")
        path_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(path_lbl)

        root.addWidget(_divider())

        btn_row = QHBoxLayout()
        modify_btn = QPushButton("Modify")
        modify_btn.clicked.connect(self._on_modify)
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet(
            "QPushButton { background: #AA4444; } QPushButton:hover { background: #883333; }"
        )
        remove_btn.clicked.connect(self._on_remove)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("flat")
        cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(modify_btn)
        btn_row.addWidget(remove_btn)
        root.addLayout(btn_row)

    def _on_modify(self) -> None:
        self._choice = "modify"
        self.accept()

    def _on_remove(self) -> None:
        self._choice = "remove"
        self.accept()

    def choice(self) -> str | None:
        return self._choice


def _do_remove(install_path: str) -> None:
    from PySide6.QtWidgets import QMessageBox
    confirm = QMessageBox.question(
        None,
        "Remove Hamster AI",
        "This will remove the startup entry, desktop shortcut, and registry record.\n\n"
        "Your data folder (data/) will NOT be deleted.\n\n"
        "Continue?",
        QMessageBox.Yes | QMessageBox.No,
    )
    if confirm != QMessageBox.Yes:
        return

    _startup_remove()

    desktop_vbs = Path.home() / "Desktop" / "HamsterAI.vbs"
    if desktop_vbs.exists():
        desktop_vbs.unlink()

    _reg_delete()

    QMessageBox.information(None, "Removed", "Hamster AI has been removed.\nYour data folder is intact.")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_install_dir() -> Path:
    # When run from installer/ sub-folder, root is one level up.
    here = Path(__file__).resolve().parent
    candidate = here.parent
    if (candidate / "app" / "main.py").exists():
        return candidate
    return here


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Hamster AI Setup")
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(_hamster_icon())

    install_dir = _resolve_install_dir()

    existing_path = _reg_read("InstallPath")
    if existing_path and Path(existing_path).exists():
        dlg = ModeDialog(existing_path)
        dlg.exec()
        choice = dlg.choice()

        if choice == "modify":
            preselected = _reg_read("SelectedPlugins", "")
            keys = [k.strip() for k in preselected.split(",") if k.strip()] if preselected else None
            wiz = HamsterWizard(Path(existing_path), preselected=keys, mode="modify")
            # skip welcome + prereqs, go straight to plugins
            wiz.setStartId(HamsterWizard.PAGE_PLUGINS)
            wiz.exec()
        elif choice == "remove":
            _do_remove(existing_path)
        # else cancelled — exit silently
    else:
        wiz = HamsterWizard(install_dir, mode="install")
        wiz.exec()

    sys.exit(0)


if __name__ == "__main__":
    main()
