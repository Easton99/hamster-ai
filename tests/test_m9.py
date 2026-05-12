"""Milestone 9 smoke test â€” plugin system: load, enable/disable, commands, crash isolation."""
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


# â”€â”€ Minimal plugin source written into temp dirs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_GOOD_PLUGIN = """\
from app.plugins.plugin_base import PluginBase

class Plugin(PluginBase):
    name = "good_plugin"
    description = "Works correctly"
    enabled_by_default = False

    def on_start(self, app):
        self.started = True
        self.events = []

    def on_stop(self, app):
        self.started = False

    def on_event(self, event, data):
        self.events.append(event)

    def get_commands(self):
        return {"/test-hello": lambda app, args: f"hello {args}"}
"""

_DEFAULT_ON_PLUGIN = """\
from app.plugins.plugin_base import PluginBase

class Plugin(PluginBase):
    name = "auto_plugin"
    description = "Enabled by default"
    enabled_by_default = True

    def on_start(self, app): pass
    def on_stop(self, app): pass
    def on_event(self, event, data): pass
    def get_commands(self): return {}
"""

_CRASH_START_PLUGIN = """\
from app.plugins.plugin_base import PluginBase

class Plugin(PluginBase):
    name = "crash_start"
    description = "Crashes on start"
    enabled_by_default = False

    def on_start(self, app): raise RuntimeError("boom on start")
    def on_stop(self, app): pass
    def on_event(self, event, data): pass
    def get_commands(self): return {}
"""

_CRASH_EVENT_PLUGIN = """\
from app.plugins.plugin_base import PluginBase

class Plugin(PluginBase):
    name = "crash_event"
    description = "Crashes on every event"
    enabled_by_default = False

    def on_start(self, app): pass
    def on_stop(self, app): pass
    def on_event(self, event, data): raise RuntimeError("boom in event")
    def get_commands(self): return {}
"""


def _write_plugin(plugins_dir: Path, folder: str, code: str) -> None:
    d = plugins_dir / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "plugin.py").write_text(code)


print("\n--- Hamster AI Milestone 9 Smoke Test ---")

# â”€â”€ CommandDispatcher.unregister â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ CommandDispatcher.unregister ]")
from app.core.commands import build_dispatcher

d = build_dispatcher()
d.register("/test-cmd", lambda app, args: "ok", "test command")
check("command registered", any(c == "test-cmd" for c, _ in d.list_commands()))
d.unregister("/test-cmd")
check("command unregistered", not any(c == "test-cmd" for c, _ in d.list_commands()))
check("unregister unknown is safe", (d.unregister("/nonexistent") or True))

# â”€â”€ Plugin loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Loading ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext
    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"
    _write_plugin(plugins_dir, "good_plugin", _GOOD_PLUGIN)
    _write_plugin(plugins_dir, "auto_plugin", _DEFAULT_ON_PLUGIN)
    ctx.start()

    pm = ctx.plugin_manager
    plugins = pm.list_plugins()
    names = [p["name"] for p in plugins]

    check("good_plugin loaded", "good_plugin" in names)
    check("auto_plugin loaded", "auto_plugin" in names)
    check("auto_plugin enabled by default", any(p["name"] == "auto_plugin" and p["enabled"] for p in plugins))
    check("good_plugin not enabled by default", any(p["name"] == "good_plugin" and not p["enabled"] for p in plugins))

    ctx.stop()

# â”€â”€ Enable / disable / commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Enable / Disable / Commands ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"
    _write_plugin(plugins_dir, "good_plugin", _GOOD_PLUGIN)
    ctx.start()
    pm = ctx.plugin_manager

    check("enable_plugin returns True", pm.enable_plugin("good_plugin"))
    check("plugin is active after enable", any(p["name"] == "good_plugin" and p["enabled"] for p in pm.list_plugins()))
    check("/test-hello registered in dispatcher", any(c == "test-hello" for c, _ in ctx.commands.list_commands()))

    result = ctx.commands.dispatch("/test-hello world", ctx)
    check("/test-hello command works", result == "hello world")

    check("idempotent enable returns True", pm.enable_plugin("good_plugin"))

    check("disable_plugin returns True", pm.disable_plugin("good_plugin"))
    check("plugin not active after disable", any(p["name"] == "good_plugin" and not p["enabled"] for p in pm.list_plugins()))
    check("/test-hello unregistered after disable", not any(c == "test-hello" for c, _ in ctx.commands.list_commands()))

    check("disable when inactive returns False", not pm.disable_plugin("good_plugin"))
    check("enable unknown returns False", not pm.enable_plugin("no_such_plugin"))

    ctx.stop()

# â”€â”€ State persistence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ State Persistence ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"
    _write_plugin(plugins_dir, "good_plugin", _GOOD_PLUGIN)
    ctx.start()
    pm = ctx.plugin_manager

    pm.enable_plugin("good_plugin")
    enabled_list = ctx.settings.get("plugins_enabled", [])
    check("enabled state persisted to settings", "good_plugin" in enabled_list)

    pm.disable_plugin("good_plugin")
    enabled_list2 = ctx.settings.get("plugins_enabled", [])
    check("disabled state removed from settings", "good_plugin" not in enabled_list2)

    ctx.stop()

# â”€â”€ Crash isolation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Crash Isolation ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"
    _write_plugin(plugins_dir, "crash_start", _CRASH_START_PLUGIN)
    _write_plugin(plugins_dir, "crash_event", _CRASH_EVENT_PLUGIN)
    _write_plugin(plugins_dir, "good_plugin", _GOOD_PLUGIN)
    ctx.start()
    pm = ctx.plugin_manager

    # Crash on start â€” enable returns False, app keeps running
    result = pm.enable_plugin("crash_start")
    check("crash-on-start returns False", result is False)
    check("crash-on-start not in active set", not any(p["name"] == "crash_start" and p["enabled"] for p in pm.list_plugins()))

    # Crash on event â€” plugin stays enabled, event dispatch doesn't propagate exception
    pm.enable_plugin("crash_event")
    check("crash-on-event plugin enabled", any(p["name"] == "crash_event" and p["enabled"] for p in pm.list_plugins()))
    try:
        ctx.event_bus.emit("user_message", {"text": "test"})
        check("event with crashing plugin doesn't raise", True)
    except Exception:
        check("event with crashing plugin doesn't raise", False)

    # Good plugin still works after crashing plugin is active
    pm.enable_plugin("good_plugin")
    plugin_instance = pm.get_plugin("good_plugin")
    ctx.event_bus.emit("user_message", {"text": "test"})
    check("good plugin receives events despite crashing neighbour",
          hasattr(plugin_instance, "events") and "user_message" in plugin_instance.events)

    ctx.stop()

# â”€â”€ Event dispatch to plugins â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Event Dispatch ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"
    _write_plugin(plugins_dir, "good_plugin", _GOOD_PLUGIN)
    ctx.start()
    pm = ctx.plugin_manager
    pm.enable_plugin("good_plugin")

    inst = pm.get_plugin("good_plugin")
    ctx.event_bus.emit("user_message", {"text": "hi"})
    ctx.event_bus.emit("work_mode_enabled")

    check("plugin received user_message event", "user_message" in inst.events)
    check("plugin received work_mode_enabled event", "work_mode_enabled" in inst.events)

    # Events stop after disable
    inst.events.clear()
    pm.disable_plugin("good_plugin")
    ctx.event_bus.emit("user_message", {"text": "hi again"})
    check("no events received after disable", "user_message" not in inst.events)

    ctx.stop()

# â”€â”€ /help includes plugin commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Help Integration ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"
    _write_plugin(plugins_dir, "good_plugin", _GOOD_PLUGIN)
    ctx.start()
    pm = ctx.plugin_manager

    help_before = ctx.commands.get_help()
    check("/test-hello not in help before enable", "test-hello" not in help_before)

    pm.enable_plugin("good_plugin")
    help_after = ctx.commands.get_help()
    check("/test-hello in help after enable", "test-hello" in help_after)

    pm.disable_plugin("good_plugin")
    help_final = ctx.commands.get_help()
    check("/test-hello removed from help after disable", "test-hello" not in help_final)

    ctx.stop()

# â”€â”€ Real session_awareness plugin loads â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ session_awareness Plugin (real) ]")
import shutil
real_plugin = ROOT / "plugins" / "session_awareness" / "plugin.py"
check("session_awareness plugin file exists", real_plugin.exists())

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    ctx = AppContext(Path(tmp))
    dest = Path(tmp) / "plugins" / "session_awareness"
    shutil.copytree(ROOT / "plugins" / "session_awareness", dest)
    ctx.start()
    pm = ctx.plugin_manager

    check("session_awareness loaded", "session_awareness" in [p["name"] for p in pm.list_plugins()])
    check("session_awareness enabled by default",
          any(p["name"] == "session_awareness" and p["enabled"] for p in pm.list_plugins()))
    check("/session command registered",
          any(c == "session" for c, _ in ctx.commands.list_commands()))

    ctx.stop()

# â”€â”€ Plugin preferences survive restart â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Preferences Survive Restart ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    # First run: enable a disabled-by-default plugin, disable a default-on one
    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"
    _write_plugin(plugins_dir, "good_plugin",  _GOOD_PLUGIN)    # default off
    _write_plugin(plugins_dir, "auto_plugin",  _DEFAULT_ON_PLUGIN)  # default on
    ctx.start()
    pm = ctx.plugin_manager

    pm.enable_plugin("good_plugin")   # turn ON a normally-off plugin
    pm.disable_plugin("auto_plugin")  # turn OFF a normally-on plugin
    ctx.stop()

    # Second run: new AppContext, same data directory
    ctx2 = AppContext(Path(tmp))
    ctx2.start()
    pm2 = ctx2.plugin_manager
    plugins2 = pm2.list_plugins()

    check("manually enabled plugin still on after restart",
          any(p["name"] == "good_plugin" and p["enabled"] for p in plugins2))
    check("manually disabled plugin still off after restart",
          any(p["name"] == "auto_plugin" and not p["enabled"] for p in plugins2))
    ctx2.stop()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"\n{'=' * 40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'=' * 40}")
sys.exit(0 if failed == 0 else 1)
