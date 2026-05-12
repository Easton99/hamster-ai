"""Milestone 17 smoke test â€” Personality Profile Editor + Per-Plugin Settings."""
import json
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


print("\n--- Hamster AI Milestone 17 Smoke Test ---\n")

# â”€â”€ personality_editor.py importable â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ Personality Editor Module ]")
try:
    from app.desktop.personality_editor import PersonalityEditor, DEFAULT_PROFILE_NAME
    check("personality_editor.py imports cleanly", True)
    check("DEFAULT_PROFILE_NAME is 'Hamster'", DEFAULT_PROFILE_NAME == "Hamster")
except ImportError as e:
    check(f"personality_editor.py imports cleanly ({e})", False)

# â”€â”€ personality_profiles.json readable â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Personality Profiles JSON ]")
profiles_path = ROOT / "config" / "personality_profiles.json"
check("personality_profiles.json exists", profiles_path.exists())

if profiles_path.exists():
    data = json.loads(profiles_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        hamster = next((p for p in data if p.get("name") == "Hamster"), None)
    else:
        hamster = data if data.get("name") == "Hamster" else None

    check("Hamster profile exists in JSON", hamster is not None)
    if hamster:
        check("Hamster profile has tone field", "tone" in hamster)
        check("Hamster profile has example_phrases", "example_phrases" in hamster)
        check("example_phrases is a list", isinstance(hamster["example_phrases"], list))

# â”€â”€ Profile file save/load round-trip â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Profile Save/Load ]")
with tempfile.TemporaryDirectory() as tmp:
    config_dir = Path(tmp) / "config"
    config_dir.mkdir()
    profile_file = config_dir / "personality_profiles.json"

    # Write a profile as list (the format the editor saves)
    profiles = [
        {
            "name": "Hamster",
            "tone": "casual, brief",
            "greeting_style": "short",
            "example_phrases": ["Hamster online."],
        },
        {
            "name": "Professional",
            "tone": "formal, concise",
            "greeting_style": "medium",
            "example_phrases": ["Good day."],
        },
    ]
    profile_file.write_text(json.dumps(profiles, indent=2), encoding="utf-8")

    # Read it back
    loaded = json.loads(profile_file.read_text(encoding="utf-8"))
    check("profile list round-trips correctly", len(loaded) == 2)
    check("Hamster profile preserved", loaded[0]["name"] == "Hamster")
    check("custom profile preserved", loaded[1]["name"] == "Professional")
    check("example_phrases preserved", loaded[1]["example_phrases"] == ["Good day."])

# â”€â”€ Per-plugin settings: config.json schema â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Per-Plugin Settings Schema ]")
plugin_configs_to_check = [
    ("extended_system_stats", ["poll_interval_seconds", "warn_cpu_above"]),
    ("process_awareness", ["show_remote_addresses"]),
    ("hardware_awareness", ["battery_warn_below", "usb_event_notifications"]),
    ("scheduled_reminders", ["queue_during_protected_modes"]),
]

for plugin_name, expected_keys in plugin_configs_to_check:
    cfg_path = ROOT / "plugins" / plugin_name / "config.json"
    check(f"{plugin_name}/config.json exists", cfg_path.exists())
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        check(f"{plugin_name} config has 'settings' key", "settings" in cfg)
        if "settings" in cfg:
            setting_keys = [s["key"] for s in cfg["settings"]]
            for k in expected_keys:
                check(f"{plugin_name} setting '{k}' defined", k in setting_keys)

# â”€â”€ Per-plugin settings key format in app settings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Per-Plugin Settings Storage ]")
from app.core.settings import Settings

with tempfile.TemporaryDirectory() as tmp:
    s = Settings(Path(tmp) / "settings.json")

    # Plugin settings are stored as "plugin.<name>.<key>"
    s.set("plugin.extended_system_stats.poll_interval_seconds", 60)
    s.set("plugin.extended_system_stats.warn_cpu_above", 85)
    s.set("plugin.hardware_awareness.battery_warn_below", 15)

    check("plugin setting round-trips (poll_interval_seconds)",
          s.get("plugin.extended_system_stats.poll_interval_seconds") == 60)
    check("plugin setting round-trips (warn_cpu_above)",
          s.get("plugin.extended_system_stats.warn_cpu_above") == 85)
    check("plugin setting round-trips (battery_warn_below)",
          s.get("plugin.hardware_awareness.battery_warn_below") == 15)
    check("different plugins don't share keys",
          s.get("plugin.process_awareness.poll_interval_seconds") is None)

# â”€â”€ Plugin config types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Plugin Config Field Types ]")
valid_types = {"toggle", "slider", "text", "dropdown", "number"}
for plugin_name, _ in plugin_configs_to_check:
    cfg_path = ROOT / "plugins" / plugin_name / "config.json"
    if not cfg_path.exists():
        continue
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    for field in cfg.get("settings", []):
        ftype = field.get("type")
        check(
            f"{plugin_name}.{field['key']} has valid type '{ftype}'",
            ftype in valid_types,
        )

print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
