"""Milestone 13 smoke test â€” Packaging (README, PyInstaller spec)."""
import sys
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


print("\n--- Hamster AI Milestone 13 Smoke Test ---\n")

# â”€â”€ README.md â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ README.md ]")
readme = ROOT / "README.md"
check("README.md exists", readme.exists())

if readme.exists():
    text = readme.read_text(encoding="utf-8")
    check("README contains setup section", "Setup" in text)
    check("README contains ollama instructions", "ollama" in text.lower())
    check("README contains run instructions", "app/main.py" in text or "python" in text.lower())
    check("README contains build section", "PyInstaller" in text or "pyinstaller" in text.lower())
    check("README contains /help command reference", "/help" in text)
    check("README mentions privacy/local-first", "local" in text.lower() or "privacy" in text.lower())

# â”€â”€ PyInstaller spec â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ hamster_ai.spec ]")
spec = ROOT / "hamster_ai.spec"
check("hamster_ai.spec exists", spec.exists())

if spec.exists():
    spec_text = spec.read_text(encoding="utf-8")
    check("spec references app/main.py entrypoint", "app/main.py" in spec_text)
    check("spec names output HamsterAI", "HamsterAI" in spec_text)
    check("spec includes config data files", "'config'" in spec_text)
    check("spec includes plugins data files", "'plugins'" in spec_text)
    check("spec sets console=False (no terminal window)", "console=False" in spec_text)
    check("spec has hidden imports", "hiddenimports" in spec_text)

# â”€â”€ requirements.txt â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ requirements.txt ]")
reqs = ROOT / "requirements.txt"
check("requirements.txt exists", reqs.exists())
if reqs.exists():
    reqs_text = reqs.read_text(encoding="utf-8")
    check("requirements lists PySide6", "PySide6" in reqs_text)
    check("requirements lists psutil", "psutil" in reqs_text)

print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
