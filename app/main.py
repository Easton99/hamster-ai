import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from app.core.app_context import AppContext
from app.desktop.tray import HamsterTray
from app.llm.ollama_client import OllamaClient
from app.llm.prompt_builder import PromptBuilder


def _show_startup_message(ctx: AppContext, tray: HamsterTray, ollama_ok: bool) -> None:
    if not ollama_ok:
        tray.showMessage(
            "Hamster AI",
            "Ollama is not running. Start it with: ollama serve",
            QSystemTrayIcon.Warning,
            5000,
        )
        return

    from app.core.greeting import get_startup_greeting
    greeting = get_startup_greeting(ctx)
    if greeting:
        tray.showMessage("Hamster AI", greeting, QSystemTrayIcon.Information, 3000)


def main() -> None:
    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)
    qt_app.setApplicationName("Hamster AI")

    ctx = AppContext(ROOT)
    ctx.start()

    client = OllamaClient(
        base_url=ctx.settings.get("ollama_url", "http://localhost:11434"),
        model=ctx.settings.get("model", "llama3.2:3b"),
    )
    builder = PromptBuilder()

    tray = HamsterTray(ctx, client, builder)
    tray.show()

    ctx.setup_model_manager(client)
    ctx.setup_hotkey(tray.open_chat)

    # Apply startup delay when launched via the Windows Run key (--startup flag).
    # Otherwise use a short 1-second delay so the tray icon is visible first.
    is_startup_launch = "--startup" in sys.argv
    delay_ms = (
        ctx.settings.get("startup_delay_seconds", 30) * 1000
        if is_startup_launch
        else 1000
    )

    ollama_ok = client.is_available()
    QTimer.singleShot(delay_ms, lambda: _show_startup_message(ctx, tray, ollama_ok))

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
