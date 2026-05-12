"""Milestone 3 smoke test â€” imports, widget instantiation, theme."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = "[PASS]"
FAIL = "[FAIL]"
results: list[tuple[str, str]] = []


def check(label: str, condition: bool) -> None:
    tag = PASS if condition else FAIL
    results.append((tag, label))
    print(f"  {tag} {label}")


print("\n--- Hamster AI Milestone 3 Smoke Test ---\n")

# â”€â”€ Imports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ Imports ]")
try:
    from PySide6.QtWidgets import QApplication
    check("PySide6 importable", True)
except ImportError as e:
    check(f"PySide6 importable â€” {e}", False)
    print("\nInstall with: pip install PySide6")
    sys.exit(1)

try:
    from app.desktop.theme import STYLESHEET, ACCENT, BG, TEXT
    check("theme module importable", True)
except Exception as e:
    check(f"theme module importable â€” {e}", False)

try:
    from app.desktop.llm_worker import LLMWorker
    check("LLMWorker importable", True)
except Exception as e:
    check(f"LLMWorker importable â€” {e}", False)

try:
    from app.desktop.chat_window import ChatWindow
    check("ChatWindow importable", True)
except Exception as e:
    check(f"ChatWindow importable â€” {e}", False)

try:
    from app.desktop.settings_window import SettingsWindow
    check("SettingsWindow importable", True)
except Exception as e:
    check(f"SettingsWindow importable â€” {e}", False)

try:
    from app.desktop.tray import HamsterTray
    from app.desktop.icons import make_hamster_icon as _make_hamster_icon
    check("HamsterTray importable", True)
except Exception as e:
    check(f"HamsterTray importable â€” {e}", False)

# â”€â”€ Theme â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Theme ]")
check("STYLESHEET is a non-empty string", isinstance(STYLESHEET, str) and len(STYLESHEET) > 100)
check("ACCENT color defined", ACCENT == "#A67C52")
check("BG color defined", BG == "#FAF7F2")
check("TEXT color defined", TEXT == "#3E2C1C")

# â”€â”€ Widget instantiation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Widget Instantiation ]")
qt_app = QApplication.instance() or QApplication(sys.argv)

from app.core.app_context import AppContext
from app.llm.ollama_client import OllamaClient
from app.llm.prompt_builder import PromptBuilder

ctx = AppContext(ROOT)
ctx.start()
client = OllamaClient(
    base_url=ctx.settings.get("ollama_url"),
    model=ctx.settings.get("model"),
)
builder = PromptBuilder()

try:
    chat_win = ChatWindow(ctx, client, builder)
    chat_win.setStyleSheet(STYLESHEET)
    check("ChatWindow created without error", True)
    check("ChatWindow has correct title", chat_win.windowTitle() == "Hamster AI")
except Exception as e:
    check(f"ChatWindow created â€” {e}", False)

try:
    settings_win = SettingsWindow(ctx)
    settings_win.setStyleSheet(STYLESHEET)
    check("SettingsWindow created without error", True)
    check("SettingsWindow has correct title", "Settings" in settings_win.windowTitle())
except Exception as e:
    check(f"SettingsWindow created â€” {e}", False)

try:
    from PySide6.QtGui import QIcon
    icon = _make_hamster_icon()
    check("Hamster tray icon created", not icon.isNull())
except Exception as e:
    check(f"Hamster tray icon created â€” {e}", False)

try:
    from PySide6.QtWidgets import QSystemTrayIcon
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = HamsterTray(ctx, client, builder)
        check("HamsterTray created without error", True)
    else:
        print("  [SKIP] System tray not available in this environment")
except Exception as e:
    check(f"HamsterTray created â€” {e}", False)

# â”€â”€ LLMWorker signals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ LLMWorker ]")
try:
    worker = LLMWorker(client, [{"role": "user", "content": "hi"}])
    check("LLMWorker instantiated", True)
    check("LLMWorker has chunk_received signal", hasattr(worker, "chunk_received"))
    check("LLMWorker has response_done signal", hasattr(worker, "response_done"))
    check("LLMWorker has request_error signal", hasattr(worker, "request_error"))
    worker.cancel()
    check("LLMWorker cancel() callable", True)
except Exception as e:
    check(f"LLMWorker â€” {e}", False)

ctx.stop()

# â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
passed = sum(1 for tag, _ in results if tag == PASS)
failed = sum(1 for tag, _ in results if tag == FAIL)
print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
