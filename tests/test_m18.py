"""Milestone 18 smoke test â€” Extended System Stats Plugin."""
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


print("\n--- Hamster AI Milestone 18 Smoke Test ---\n")

# â”€â”€ Observer modules â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ Observer Modules ]")
from app.observer.gpu import get_gpu_stats, GpuStats
gpus = get_gpu_stats()
check("get_gpu_stats() returns a list", isinstance(gpus, list))
if gpus:
    g = gpus[0]
    check("GpuStats has name", isinstance(g.name, str))
    check("GpuStats load_percent is 0-100", 0 <= g.load_percent <= 100)
    check("GpuStats memory_total_mb > 0", g.memory_total_mb > 0)
else:
    check("get_gpu_stats() returns empty list when no GPU lib (acceptable)", True)

from app.observer.network_stats import NetworkStatsTracker, NetworkSnapshot
tracker = NetworkStatsTracker()
snap = tracker.snapshot()
check("NetworkStatsTracker.snapshot() returns NetworkSnapshot", isinstance(snap, NetworkSnapshot))
check("NetworkSnapshot has bytes_sent", isinstance(snap.bytes_sent, int))
check("NetworkSnapshot has bytes_recv", isinstance(snap.bytes_recv, int))
check("NetworkSnapshot sent_rate_kbps >= 0", snap.sent_rate_kbps >= 0)
check("NetworkSnapshot recv_rate_kbps >= 0", snap.recv_rate_kbps >= 0)

# â”€â”€ Plugin file exists â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin File ]")
plugin_dir = ROOT / "plugins" / "extended_system_stats"
check("plugin directory exists", plugin_dir.exists())
check("plugin.py exists", (plugin_dir / "plugin.py").exists())
check("config.json exists", (plugin_dir / "config.json").exists())

# â”€â”€ Plugin loads and runs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Load ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext
    ctx = AppContext(Path(tmp))
    dest = Path(tmp) / "plugins" / "extended_system_stats"
    shutil.copytree(plugin_dir, dest)
    ctx.start()
    pm = ctx.plugin_manager

    check("extended_system_stats plugin found", "extended_system_stats" in [p["name"] for p in pm.list_plugins()])

    result = pm.enable_plugin("extended_system_stats")
    check("extended_system_stats enables without crash", result is True)

    # Give poll thread a moment
    import time
    time.sleep(2)

    plugin_inst = pm.get_plugin("extended_system_stats")

    # â”€â”€ Commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Commands ]")
    for cmd in ("/system", "/top-processes", "/disk", "/network", "/gpu"):
        short = cmd.lstrip("/")
        check(f"{cmd} command registered", any(c == short for c, _ in ctx.commands.list_commands()))

    resp = ctx.commands.dispatch("/system", ctx)
    check("/system returns a non-empty string", isinstance(resp, str) and len(resp) > 0)

    resp = ctx.commands.dispatch("/disk", ctx)
    check("/disk returns disk info or waiting message", isinstance(resp, str))

    resp = ctx.commands.dispatch("/network", ctx)
    check("/network returns string", isinstance(resp, str))

    resp = ctx.commands.dispatch("/gpu", ctx)
    check("/gpu returns string (may say no GPU)", isinstance(resp, str))

    resp = ctx.commands.dispatch("/top-processes", ctx)
    check("/top-processes returns process info", isinstance(resp, str) and len(resp) > 0)

    # â”€â”€ Snapshot structure â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[ Snapshot Structure ]")
    snap_data = plugin_inst.get_snapshot()
    check("snapshot is a dict", isinstance(snap_data, dict))
    if snap_data:
        check("snapshot has cpu_percent", "cpu_percent" in snap_data)
        check("snapshot has ram_percent", "ram_percent" in snap_data)
        check("snapshot has disks list", isinstance(snap_data.get("disks"), list))
        check("snapshot cpu_percent in range 0-100",
              isinstance(snap_data.get("cpu_percent"), (int, float)) and
              0 <= snap_data["cpu_percent"] <= 100)

    ctx.stop()

print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
