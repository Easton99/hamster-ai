"""Milestone 19 smoke test â€” Process Awareness Plugin."""
import sys
import shutil
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


print("\n--- Hamster AI Milestone 19 Smoke Test ---\n")

# â”€â”€ Observer modules â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ Observer Modules ]")
from app.observer.process_list import get_top_processes, get_internet_processes, ProcessInfo

procs = get_top_processes(5)
check("get_top_processes returns a list", isinstance(procs, list))
check("get_top_processes returns at most 5", len(procs) <= 5)
if procs:
    p = procs[0]
    check("ProcessInfo has pid", isinstance(p.pid, int) and p.pid > 0)
    check("ProcessInfo has name", isinstance(p.name, str) and len(p.name) > 0)
    check("ProcessInfo cpu_percent >= 0", p.cpu_percent >= 0)
    check("ProcessInfo ram_mb >= 0", p.ram_mb >= 0)
    check("ProcessInfo has status", isinstance(p.status, str))

inet_procs = get_internet_processes()
check("get_internet_processes returns a list", isinstance(inet_procs, list))
if inet_procs:
    check("internet process has has_network=True", all(p.has_network for p in inet_procs))

from app.observer.startup_programs import get_startup_programs, StartupEntry
startup = get_startup_programs()
check("get_startup_programs returns a list", isinstance(startup, list))
if startup:
    entry = startup[0]
    check("StartupEntry has name", isinstance(entry.name, str))
    check("StartupEntry has path", isinstance(entry.path, str))
    check("StartupEntry has source", isinstance(entry.source, str))

# â”€â”€ Plugin files â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Files ]")
plugin_dir = ROOT / "plugins" / "process_awareness"
check("plugin directory exists", plugin_dir.exists())
check("plugin.py exists", (plugin_dir / "plugin.py").exists())
check("config.json exists", (plugin_dir / "config.json").exists())

# â”€â”€ Plugin loads and commands work â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Load + Commands ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext
    ctx = AppContext(Path(tmp))
    dest = Path(tmp) / "plugins" / "process_awareness"
    shutil.copytree(plugin_dir, dest)
    ctx.start()
    pm = ctx.plugin_manager

    check("process_awareness plugin found", "process_awareness" in [p["name"] for p in pm.list_plugins()])

    result = pm.enable_plugin("process_awareness")
    check("process_awareness enables without crash", result is True)

    for cmd in ("/processes", "/internet-apps", "/startup-programs", "/kill"):
        short = cmd.lstrip("/")
        check(f"{cmd} command registered", any(c == short for c, _ in ctx.commands.list_commands()))

    resp = ctx.commands.dispatch("/processes", ctx)
    check("/processes returns string", isinstance(resp, str) and len(resp) > 0)
    check("/processes shows process info", "CPU" in resp or "process" in resp.lower() or "mode" in resp.lower())

    resp = ctx.commands.dispatch("/internet-apps", ctx)
    check("/internet-apps returns string", isinstance(resp, str))

    resp = ctx.commands.dispatch("/startup-programs", ctx)
    check("/startup-programs returns string", isinstance(resp, str))

    # /kill should ask for confirmation, not actually kill anything
    resp = ctx.commands.dispatch("/kill python", ctx)
    check("/kill asks for confirmation (does not auto-kill)", "confirm" in resp.lower() or "/kill-confirm" in resp)

    resp = ctx.commands.dispatch("/kill", ctx)
    check("/kill with no args returns usage", "Usage" in resp or "usage" in resp.lower())

    # â”€â”€ Protected mode blocks process list â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Protected Mode ]")
    ctx.modes.enable_work_mode()
    resp = ctx.commands.dispatch("/processes", ctx)
    check("/processes blocked during Work Mode", "mode" in resp.lower() or "available" in resp.lower() or "not" in resp.lower())
    ctx.modes.disable_work_mode()

    ctx.stop()

print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
