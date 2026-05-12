"""Milestone 6 smoke test â€” diagnostics, health checks, self-fix."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = "[PASS]"
FAIL = "[FAIL]"
results: list[tuple[str, str]] = []


def check(label: str, condition: bool) -> None:
    tag = PASS if condition else FAIL
    results.append((tag, label))
    print(f"  {tag} {label}")


print("\n--- Hamster AI Milestone 6 Smoke Test ---\n")

from app.core.app_context import AppContext
ctx = AppContext(ROOT)
ctx.start()

# â”€â”€ Health Checks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ Health Checks ]")
from app.core.health_checks import run_all, OK, WARNING, FAIL as FAIL_STATUS

results_hc = run_all(ctx)
check("run_all returns a list", isinstance(results_hc, list))
check("at least 5 checks ran", len(results_hc) >= 5)

names = [r.name for r in results_hc]
for expected in ("Ollama", "Model", "Database", "Disk space", "Config"):
    check(f"'{expected}' check present", expected in names)

db_result = next(r for r in results_hc if r.name == "Database")
check("Database check passes", db_result.status == OK)

disk_result = next(r for r in results_hc if r.name == "Disk space")
check("Disk space check ran", disk_result.status in (OK, WARNING, FAIL_STATUS))

for r in results_hc:
    check(f"  '{r.name}' has message", bool(r.message))

# â”€â”€ Diagnostics facade â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Diagnostics ]")
check("Diagnostics created", ctx.diagnostics is not None)

hc = ctx.diagnostics.run_checks()
check("run_checks returns results", len(hc) > 0)

errors = ctx.diagnostics.recent_errors()
check("recent_errors returns a list", isinstance(errors, list))

logs = ctx.diagnostics.all_recent_logs(50)
check("all_recent_logs returns lines", isinstance(logs, list))

# â”€â”€ Self-Fix â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Self-Fix ]")
from app.core.self_fix import SelfFix
sf = SelfFix(ctx)

suggestions = sf.suggestions_for(hc)
check("suggestions_for returns a list", isinstance(suggestions, list))

# Force a fixable scenario: fake a failed result
from app.core.health_checks import HealthResult
fake_results = [HealthResult("Test", FAIL_STATUS, "Missing", fix_key="recreate_folders")]
suggs = sf.suggestions_for(fake_results)
check("fix suggestion returned for known fix_key", len(suggs) == 1)
check("suggestion has correct key", suggs[0].key == "recreate_folders")
check("suggestion has label", bool(suggs[0].label))

# Apply a safe fix (recreate_folders â€” idempotent)
ok, msg = sf.apply("recreate_folders")
check("recreate_folders fix applies successfully", ok)
check("fix returns a message", bool(msg))

# Unknown fix key
ok, msg = sf.apply("nonexistent_fix")
check("unknown fix key returns False", not ok)

# â”€â”€ Commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Diagnostic Commands ]")
d = ctx.commands

resp = d.dispatch("/health", ctx)
check("/health returns check results", "âœ“" in resp or "âœ—" in resp or "!" in resp)
check("/health includes Ollama", "Ollama" in resp)

resp = d.dispatch("/errors", ctx)
check("/errors returns a string", isinstance(resp, str))

resp = d.dispatch("/fix", ctx)
check("/fix returns a string", isinstance(resp, str))

# â”€â”€ Export Bundle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Export Bundle ]")
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    bundle = ctx.diagnostics.export_bundle(Path(tmp))
    check("export_bundle creates a zip file", bundle.exists() and bundle.suffix == ".zip")
    import zipfile
    with zipfile.ZipFile(bundle) as zf:
        names = zf.namelist()
    check("zip contains health_checks.txt", "health_checks.txt" in names)
    check("zip contains settings_redacted.json", "settings_redacted.json" in names)

ctx.stop()

# â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
passed = sum(1 for tag, _ in results if tag == PASS)
failed = sum(1 for tag, _ in results if tag == FAIL)
print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
