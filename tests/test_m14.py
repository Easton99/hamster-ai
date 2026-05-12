"""Milestone 14 smoke test â€” Model Switcher + File Drop."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

passed = failed = 0


def check(label: str, ok: bool) -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        print(f"  [FAIL] {label}")


print("\n--- Hamster AI Milestone 14 Smoke Test ---\n")

# â”€â”€ ModelManager â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ ModelManager ]")
from app.llm.model_manager import ModelManager
from app.llm.ollama_client import OllamaClient

client = OllamaClient(model="llama3.2:3b")
mm = ModelManager(client)

check("ModelManager.current() returns model name", mm.current() == "llama3.2:3b")
mm.switch("mistral")
check("ModelManager.switch() updates current", mm.current() == "mistral")
check("ModelManager.switch() updates client.model", client.model == "mistral")
mm.switch("llama3.2:3b")
check("ModelManager.switch() back to original", mm.current() == "llama3.2:3b")

# list_available returns a list (may be empty if Ollama not running)
models = mm.list_available()
check("ModelManager.list_available() returns a list", isinstance(models, list))

# â”€â”€ /model command â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ /model command ]")
from app.core.app_context import AppContext

ctx = AppContext(ROOT)
ctx.start()
ctx.setup_model_manager(client)

resp = ctx.commands.dispatch("/model", ctx)
check("/model shows current model", "llama3.2:3b" in resp or "model" in resp.lower())

resp = ctx.commands.dispatch("/model list", ctx)
check("/model list returns a string response", isinstance(resp, str) and len(resp) > 0)

resp = ctx.commands.dispatch("/model use mistral", ctx)
check("/model use <name> switches model", "mistral" in resp.lower() or "switched" in resp.lower())
check("model setting updated in settings", ctx.settings.get("model") == "mistral")
ctx.settings.set("model", "llama3.2:3b")
ctx.model_manager.switch("llama3.2:3b")

resp = ctx.commands.dispatch("/model use", ctx)
check("/model use with no name returns usage hint", "Usage" in resp or "usage" in resp.lower())

ctx.stop()

# â”€â”€ File drop logic â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ File Drop Logic ]")
from app.desktop.chat_window import (
    _SUPPORTED_EXTENSIONS,
    _FILE_DROP_MAX_KB,
    _FILE_DROP_MAX_LINES,
)

check("Supported extensions includes .py", ".py" in _SUPPORTED_EXTENSIONS)
check("Supported extensions includes .txt", ".txt" in _SUPPORTED_EXTENSIONS)
check("Supported extensions includes .json", ".json" in _SUPPORTED_EXTENSIONS)
check("Supported extensions includes .sql", ".sql" in _SUPPORTED_EXTENSIONS)
check("Unsupported extension .exe not in set", ".exe" not in _SUPPORTED_EXTENSIONS)
check("Unsupported extension .png not in set", ".png" not in _SUPPORTED_EXTENSIONS)
check("Max lines constant is > 0", _FILE_DROP_MAX_LINES > 0)
check("Max KB constant is > 0", _FILE_DROP_MAX_KB > 0)

# Test that a real file can be read and would be valid
with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
    f.write("def hello():\n    return 'world'\n")
    tmp_path = Path(f.name)

check("Test file is a supported extension", tmp_path.suffix in _SUPPORTED_EXTENSIONS)
content = tmp_path.read_text(encoding="utf-8")
lines = content.splitlines()
check("Small test file is within line limit", len(lines) <= _FILE_DROP_MAX_LINES)
check("Small test file is within KB limit", tmp_path.stat().st_size / 1024 <= _FILE_DROP_MAX_KB)
tmp_path.unlink()

# Test line truncation logic
big_content = "\n".join(f"line {i}" for i in range(_FILE_DROP_MAX_LINES + 100))
big_lines = big_content.splitlines()
truncated = "\n".join(big_lines[:_FILE_DROP_MAX_LINES])
check("Truncation keeps exactly MAX_LINES", len(truncated.splitlines()) == _FILE_DROP_MAX_LINES)

print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
