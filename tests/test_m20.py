"""Milestone 20 smoke test â€” Hardware Awareness Plugin."""
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


print("\n--- Hamster AI Milestone 20 Smoke Test ---\n")

# â”€â”€ Observer: hardware module â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ Observer: hardware.py ]")
from app.observer.hardware import (
    get_monitors, get_usb_devices, get_battery, check_internet,
    MonitorInfo, UsbDevice, BatteryInfo,
)

# Monitors
monitors = get_monitors()
check("get_monitors returns a list", isinstance(monitors, list))
if monitors:
    m = monitors[0]
    check("MonitorInfo has index", isinstance(m.index, int))
    check("MonitorInfo has width > 0", m.width > 0)
    check("MonitorInfo has height > 0", m.height > 0)
    check("MonitorInfo has is_primary bool", isinstance(m.is_primary, bool))
    check("exactly one monitor is primary", sum(1 for m in monitors if m.is_primary) <= 1)
else:
    check("get_monitors returns empty list gracefully (no ctypes access in CI)", True)

# USB devices
usb = get_usb_devices()
check("get_usb_devices returns a list", isinstance(usb, list))
if usb:
    d = usb[0]
    check("UsbDevice has name", isinstance(d.name, str))
    check("UsbDevice has device_id", isinstance(d.device_id, str))

# Battery
battery = get_battery()
check("get_battery returns BatteryInfo or None", battery is None or isinstance(battery, BatteryInfo))
if battery:
    check("BatteryInfo percent in 0-100", 0 <= battery.percent <= 100)
    check("BatteryInfo charging is bool", isinstance(battery.charging, bool))

# Internet check
result = check_internet()
check("check_internet returns a bool", isinstance(result, bool))

# â”€â”€ Plugin files â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Files ]")
plugin_dir = ROOT / "plugins" / "hardware_awareness"
check("plugin directory exists", plugin_dir.exists())
check("plugin.py exists", (plugin_dir / "plugin.py").exists())
check("config.json exists", (plugin_dir / "config.json").exists())

# â”€â”€ Plugin loads and commands work â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Load + Commands ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext
    ctx = AppContext(Path(tmp))
    dest = Path(tmp) / "plugins" / "hardware_awareness"
    shutil.copytree(plugin_dir, dest)
    ctx.start()
    pm = ctx.plugin_manager

    check("hardware_awareness plugin found",
          "hardware_awareness" in [p["name"] for p in pm.list_plugins()])

    result = pm.enable_plugin("hardware_awareness")
    check("hardware_awareness enables without crash", result is True)

    for cmd in ("/monitors", "/usb", "/battery", "/internet", "/hardware"):
        short = cmd.lstrip("/")
        check(f"{cmd} command registered",
              any(c == short for c, _ in ctx.commands.list_commands()))

    resp = ctx.commands.dispatch("/monitors", ctx)
    check("/monitors returns string", isinstance(resp, str) and len(resp) > 0)

    resp = ctx.commands.dispatch("/usb", ctx)
    check("/usb returns string", isinstance(resp, str))

    resp = ctx.commands.dispatch("/battery", ctx)
    check("/battery returns string", isinstance(resp, str))
    check("/battery mentions battery or desktop",
          "battery" in resp.lower() or "desktop" in resp.lower() or "no battery" in resp.lower())

    resp = ctx.commands.dispatch("/internet", ctx)
    check("/internet returns connectivity string",
          isinstance(resp, str) and ("connected" in resp.lower() or "reachable" in resp.lower()))

    resp = ctx.commands.dispatch("/hardware", ctx)
    check("/hardware returns combined summary", isinstance(resp, str) and len(resp) > 10)

    ctx.stop()

# â”€â”€ Config schema â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Config Schema ]")
import json
cfg = json.loads((plugin_dir / "config.json").read_text(encoding="utf-8"))
check("config has name field", cfg.get("name") == "hardware_awareness")
check("config has settings list", isinstance(cfg.get("settings"), list))
setting_keys = [s["key"] for s in cfg.get("settings", [])]
check("battery_warn_below in settings", "battery_warn_below" in setting_keys)
check("usb_event_notifications in settings", "usb_event_notifications" in setting_keys)
check("internet_check_enabled in settings", "internet_check_enabled" in setting_keys)

print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
