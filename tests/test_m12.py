"""Milestone 12 smoke test â€” Audio Plugins (voice_output, discord_translation)."""
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

# â”€â”€ Plugin folders exist â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Folder Structure ]")
check("voice_output/plugin.py exists",
      (ROOT / "plugins" / "voice_output" / "plugin.py").exists())
check("voice_output/config.json exists",
      (ROOT / "plugins" / "voice_output" / "config.json").exists())
check("discord_translation/plugin.py exists",
      (ROOT / "plugins" / "discord_translation" / "plugin.py").exists())
check("discord_translation/config.json exists",
      (ROOT / "plugins" / "discord_translation" / "config.json").exists())
check("audio_awareness/plugin.py exists",
      (ROOT / "plugins" / "audio_awareness" / "plugin.py").exists())

# â”€â”€ voice_output: imports cleanly and has correct metadata â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

# â”€â”€ voice_output: _strip_markdown helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ _strip_markdown ]")
check("strips ** bold markers",
      "**bold**" not in vo_mod._strip_markdown("**bold**"))
check("strips backticks",
      "`code`" not in vo_mod._strip_markdown("`code`"))
check("preserves plain text",
      vo_mod._strip_markdown("hello world") == "hello world")

# â”€â”€ discord_translation: imports cleanly â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ discord_translation Plugin ]")

dt_src = ROOT / "plugins" / "discord_translation" / "plugin.py"
spec2 = importlib.util.spec_from_file_location("dt_plugin", dt_src)
dt_mod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(dt_mod)

check("discord_translation Plugin class exists", hasattr(dt_mod, "Plugin"))
check("discord_translation disabled by default", dt_mod.Plugin.enabled_by_default is False)
check("discord_translation has /translate command",
      "/translate" in dt_mod.Plugin().get_commands())
check("discord_translation has /captions command",
      "/captions" in dt_mod.Plugin().get_commands())

# â”€â”€ discord_translation: helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ discord_translation Helpers ]")

import struct

# _to_mono_16k: stereo 48000 â†’ mono 16000
n = 480  # 10 ms at 48000 Hz
stereo_raw = struct.pack(f"<{n * 2}h", *([1000, -1000] * n))
mono_16k = dt_mod._to_mono_16k(stereo_raw, n_channels=2, host_rate=48000)
expected_samples = int(n * 16000 / 48000)
actual_samples = len(mono_16k) // 2
check("_to_mono_16k produces correct sample count",
      abs(actual_samples - expected_samples) <= 2)

# _frame_is_speech with no VAD â€” energy gate
loud = struct.pack("<160h", *([10000] * 160))
quiet = struct.pack("<160h", *([0] * 160))
check("_frame_is_speech: loud frame detected as speech (no VAD)",
      dt_mod._frame_is_speech(loud, None, 16000) is True)
check("_frame_is_speech: silent frame not speech (no VAD)",
      dt_mod._frame_is_speech(quiet, None, 16000) is False)

# â”€â”€ /captions returns helpful message when empty â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ /captions command ]")

class _FakeApp2:
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
        @staticmethod
        def emit(*a): pass
    class settings:
        @staticmethod
        def get(k, d=None): return d
    class modes:
        work_mode = False
        private_mode = False
        game_safe_mode = False

p2 = dt_mod.Plugin()
p2.on_start(_FakeApp2())
result = p2._cmd_captions(_FakeApp2(), "")
check("/captions returns 'No captions yet' when empty", "no captions" in result.lower())
p2.on_stop(_FakeApp2())

# â”€â”€ Plugin loads via PluginManager in full AppContext â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ PluginManager Integration ]")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    from app.core.app_context import AppContext

    ctx = AppContext(Path(tmp))
    plugins_dir = Path(tmp) / "plugins"

    # Copy all M12 plugins into temp dir
    for name in ("voice_output", "discord_translation", "audio_awareness"):
        src = ROOT / "plugins" / name
        if src.exists():
            shutil.copytree(src, plugins_dir / name)
        else:
            # Create stub so PluginManager doesn't crash
            (plugins_dir / name).mkdir(parents=True)

    ctx.start()
    pm = ctx.plugin_manager
    plugin_names = [p["name"] for p in pm.list_plugins()]

    check("voice_output loaded by PluginManager",
          "voice_output" in plugin_names)
    check("discord_translation loaded by PluginManager",
          "discord_translation" in plugin_names)
    check("audio_awareness loaded by PluginManager",
          "audio_awareness" in plugin_names)

    check("voice_output disabled by default in manager",
          any(p["name"] == "voice_output" and not p["enabled"] for p in pm.list_plugins()))
    check("discord_translation disabled by default in manager",
          any(p["name"] == "discord_translation" and not p["enabled"] for p in pm.list_plugins()))

    ctx.stop()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"\n{'=' * 40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'=' * 40}")
sys.exit(0 if failed == 0 else 1)
