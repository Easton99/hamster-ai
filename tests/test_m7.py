"""Milestone 7 smoke test â€” PC context: active window, idle, CPU/RAM, fullscreen."""
import sys
import time
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


print("\n--- Hamster AI Milestone 7 Smoke Test ---")

# â”€â”€ active_window â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Active Window ]")
from app.observer.active_window import get_active_window

proc, title = get_active_window()
check("get_active_window returns a tuple", isinstance((proc, title), tuple))
check("process name is a string", isinstance(proc, str))
check("window title is a string", isinstance(title, str))
print(f"    process='{proc}'  title='{title}'")

# â”€â”€ idle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Idle Detection ]")
from app.observer.idle import get_idle_seconds

idle = get_idle_seconds()
check("get_idle_seconds returns an int", isinstance(idle, int))
check("idle seconds is non-negative", idle >= 0)
print(f"    idle={idle}s")

# â”€â”€ system usage â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ System Usage ]")
from app.observer.system_usage import get_cpu_percent, get_ram_percent

# Prime psutil (first call returns 0.0)
import psutil
psutil.cpu_percent(interval=None)
time.sleep(0.2)

cpu = get_cpu_percent()
ram = get_ram_percent()
check("get_cpu_percent returns a float", isinstance(cpu, float))
check("cpu is in valid range or -1", cpu == -1.0 or 0.0 <= cpu <= 100.0)
check("get_ram_percent returns a float", isinstance(ram, float))
check("ram is in valid range or -1", ram == -1.0 or 0.0 <= ram <= 100.0)
print(f"    cpu={cpu:.1f}%  ram={ram:.1f}%")

# â”€â”€ fullscreen â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Fullscreen Detection ]")
from app.observer.fullscreen import is_fullscreen

fs = is_fullscreen()
check("is_fullscreen returns a bool", isinstance(fs, bool))
print(f"    fullscreen={fs}")

# â”€â”€ protected apps â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Protected Apps ]")
from app.observer.protected_apps import is_protected

check("keepass.exe triggers protection", is_protected("keepass.exe", ""))
check("bitwarden triggers protection", is_protected("Bitwarden.exe", ""))
check("incognito title triggers protection", is_protected("chrome.exe", "New Tab - Incognito"))
check("private browsing triggers protection", is_protected("firefox.exe", "Mozilla Firefox (Private Browsing)"))
check("inprivate triggers protection", is_protected("msedge.exe", "InPrivate â€” Microsoft Edge"))
check("normal app does not trigger", not is_protected("Code.exe", "main.py â€” VS Code"))
check("case insensitive match", is_protected("KEEPASS.EXE", ""))

# â”€â”€ PCSnapshot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ PCSnapshot ]")
from app.observer.pc_context import PCSnapshot

snap_empty = PCSnapshot()
check("empty snapshot produces empty context string", snap_empty.to_context_string() == "")

snap = PCSnapshot(
    active_process="Code.exe",
    active_title="main.py â€” VS Code",
    idle_seconds=0,
    cpu_percent=42.0,
    ram_percent=61.0,
    is_fullscreen=False,
)
ctx = snap.to_context_string()
check("context string is non-empty", bool(ctx))
check("context string contains process name", "Code.exe" in ctx)
check("context string contains window title", "VS Code" in ctx)
check("context string contains CPU", "42%" in ctx)
check("context string contains RAM", "61%" in ctx)

snap_idle = PCSnapshot(active_process="chrome.exe", idle_seconds=310, cpu_percent=-1.0, ram_percent=-1.0)
ctx_idle = snap_idle.to_context_string()
check("idle > 5min shown in context", "idle" in ctx_idle.lower() or "5 min" in ctx_idle)

snap_fs = PCSnapshot(active_process="game.exe", is_fullscreen=True, cpu_percent=-1.0, ram_percent=-1.0)
ctx_fs = snap_fs.to_context_string()
check("fullscreen noted in context", "fullscreen" in ctx_fs.lower())

# title same as process â€” should not duplicate
snap_same = PCSnapshot(active_process="code.exe", active_title="code.exe", cpu_percent=-1.0, ram_percent=-1.0)
ctx_same = snap_same.to_context_string()
check("title not duplicated when same as process", ctx_same.count("code.exe") == 1)

# â”€â”€ PCContextCollector â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ PCContextCollector ]")
import tempfile
from app.core.app_context import AppContext

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx_app = AppContext(Path(tmp))
    ctx_app.start()

    collector = ctx_app.pc_context
    check("pc_context exists on AppContext", collector is not None)

    # Wait one poll cycle
    time.sleep(6)

    snap2 = collector.get_snapshot()
    check("snapshot is a PCSnapshot", isinstance(snap2, PCSnapshot))
    check("snapshot has a timestamp", snap2.timestamp is not None)
    check("cpu_percent populated", snap2.cpu_percent >= 0)
    check("ram_percent populated", snap2.ram_percent >= 0)
    check("idle_seconds is int", isinstance(snap2.idle_seconds, int))
    print(f"    cpu={snap2.cpu_percent:.1f}%  ram={snap2.ram_percent:.1f}%  idle={snap2.idle_seconds}s  proc='{snap2.active_process}'")

    ctx_app.stop()

# â”€â”€ PromptBuilder integration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ PromptBuilder + PC Context ]")
from app.llm.prompt_builder import PromptBuilder

builder = PromptBuilder()
snap_llm = PCSnapshot(
    active_process="Code.exe",
    active_title="hamster-ai â€” VS Code",
    idle_seconds=0,
    cpu_percent=30.0,
    ram_percent=55.0,
)
messages = builder.build([], "hello", pc_snapshot=snap_llm)
system_msg = messages[0]["content"]

check("system message contains PC context header", "PC context" in system_msg)
check("system message contains active process", "Code.exe" in system_msg)
check("system message contains CPU", "30%" in system_msg)

# no snapshot â€” context block should be absent
messages_no_snap = builder.build([], "hello")
check("no snapshot = no PC context block", "PC context" not in messages_no_snap[0]["content"])

# extra_context still works alongside pc_snapshot
messages_both = builder.build([], "hi", extra_context="Custom note.", pc_snapshot=snap_llm)
check("extra_context and pc_snapshot both present", "Custom note." in messages_both[0]["content"] and "Code.exe" in messages_both[0]["content"])

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"\n{'=' * 40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'=' * 40}")
sys.exit(0 if failed == 0 else 1)
