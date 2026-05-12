"""Milestone 12 smoke test — Audio Plugins (voice_output, audio_awareness)."""
import importlib.util
import shutil
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


print("\n--- Hamster AI Milestone 12 Smoke Test ---")

# ── Plugin folders exist ────────────────────────────────────────────────────
print("\n[ Plugin Folder Structure ]")
check("voice_output/plugin.py exists",
      (ROOT / "plugins" / "voice_output" / "plugin.py").exists())
check("voice_output/config.json exists",
      (ROOT / "plugins" / "voice_output" / "config.json").exists())
check("audio_awareness/plugin.py exists",
      (ROOT / "plugins" / "audio_awareness" / "plugin.py").exists())

# ── voice_output: imports cleanly and has correct metadata ──────────────────
print("\n[ voice_output Plugin ]")

vo_src = ROOT / "plugins" / "voice_output" / "plugin.py"
spec = importlib.util.spec_from_file_location("vo_plugin", vo_src)
vo_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vo_mod)

check("voice_output Plugin class exists", hasattr(vo_mod, "Plugin"))
check("voice_output disabled by default", vo_mod.Plugin.enabled_by_default is False)
check("voice_output has /voice command",  "/voice" in vo_mod.Plugin().get_commands())
check("voice_output has /voice-test command", "/voice-test" in vo_mod.Plugin().get_commands())

# Test graceful degradation without pyttsx3
vo_mod_orig_ok = vo_mod._PYTTSX3_OK
try:
    vo_mod._PYTTSX3_OK = False
    p = vo_mod.Plugin()

    class _FakeApp:
        class logger:
            @staticmethod
            def warning(m): pass
            @staticmethod
            def error(m): pass
            @staticmethod
            def info(m): pass
            @staticmethod
            def debug(m): pass
        class event_bus:
            @staticmethod
            def subscribe(*a): pass
            @staticmethod
            def unsubscribe(*a): pass
        class settings:
            @staticmethod
            def get(k, d=None): return d
        class modes:
            work_mode = False
            private_mode = False
            game_safe_mode = False
            focus_mode = False

    fa = _FakeApp()
    p.on_start(fa)
    result = p._cmd_voice(fa, "")
    check("voice_output: graceful message when pyttsx3 missing",
          "unavailable" in result.lower() or "install" in result.lower())
    p.on_stop(fa)
finally:
    vo_mod._PYTTSX3_OK = vo_mod_orig_ok

# ── voice_output: _strip_markdown helper ────────────────────────────────────
print("\n[ _strip_markdown ]")
check("strips ** bold markers",
      "**bold**" not in vo_mod._strip_markdown("**bold**"))
check("strips backticks",
      "`code`" not in vo_mod._strip_markdown("`code`"))
check("preserves plain text",
      vo_mod._strip_markdown("hello world") == "hello world")

# ── Plugin loads via PluginManager in full AppContext ───────────────────────
print("\n[ PluginManager Integration ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext

    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"

    for name in ("voice_output", "audio_awareness"):
        src = ROOT / "plugins" / name
        if src.exists():
            shutil.copytree(src, plugins_dir / name)
        else:
            (plugins_dir / name).mkdir(parents=True)

    ctx.start()
    pm = ctx.plugin_manager
    plugin_names = [p["name"] for p in pm.list_plugins()]

    check("voice_output loaded by PluginManager",
          "voice_output" in plugin_names)
    check("audio_awareness loaded by PluginManager",
          "audio_awareness" in plugin_names)
    check("voice_output disabled by default in manager",
          any(p["name"] == "voice_output" and not p["enabled"] for p in pm.list_plugins()))

    ctx.stop()

# ────────────────────────────────────────────────────────────────────────────
print(f"\n{'=' * 40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'=' * 40}")
sys.exit(0 if failed == 0 else 1)
