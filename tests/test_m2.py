"""Milestone 2 smoke test â€” prompt builder (offline) + live Ollama round-trip."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.llm.ollama_client import OllamaClient, OllamaError
from app.llm.prompt_builder import PromptBuilder

PASS = "[PASS]"
FAIL = "[FAIL]"
results: list[tuple[str, str]] = []


def check(label: str, condition: bool) -> None:
    tag = PASS if condition else FAIL
    results.append((tag, label))
    print(f"  {tag} {label}")


print("\n--- Hamster AI Milestone 2 Smoke Test ---\n")

# â”€â”€ Prompt Builder (no network needed) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("[ Prompt Builder ]")
builder = PromptBuilder(max_history_turns=5)

msgs = builder.build([], "Hello")
check("System message is first", msgs[0]["role"] == "system")
check("System prompt contains core rules", "privacy-first" in msgs[0]["content"])
check("Current time injected into system prompt", "Current time:" in msgs[0]["content"])
check("User message is last", msgs[-1]["role"] == "user" and msgs[-1]["content"] == "Hello")
check("No extra messages for empty history", len(msgs) == 2)

history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(30)]
msgs_trimmed = builder.build(history, "new")
# max 5 turns = 10 history messages + system + user = 12
check("History trimmed to max_history_turns", len(msgs_trimmed) <= 12)

extra = builder.build([], "Hi", extra_context="App: VS Code")
check("Extra context injected", "VS Code" in extra[0]["content"])

# â”€â”€ Ollama Client â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[ Ollama Client ]")
client = OllamaClient()
available = client.is_available()
check("Ollama is running", available)

if available:
    try:
        models = client.list_models()
        check("list_models returns a list", isinstance(models, list))

        installed = client.model in models
        check(f"Model '{client.model}' is installed", installed)

        if installed:
            print(f"\n[ Live Chat Round-Trip â€” model: {client.model} ]")
            msgs = builder.build([], "Reply with exactly the single word: Hamster")
            response = client.chat(msgs)
            check("Got non-empty response", len(response.strip()) > 0)
            print(f"  model replied: {response.strip()[:120]!r}")
        else:
            print(f"  [SKIP] Model not installed. Run: ollama pull {client.model}")

    except OllamaError as exc:
        check("Ollama API reachable", False)
        print(f"  error: {exc}")
else:
    print("  [SKIP] Ollama not running â€” skipping API and chat tests.")
    print("         Start it with: ollama serve")

# â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
passed = sum(1 for tag, _ in results if tag == PASS)
failed = sum(1 for tag, _ in results if tag == FAIL)
print(f"\n{'='*40}")
print(f"  {passed} passed  |  {failed} failed")
print(f"{'='*40}\n")
sys.exit(0 if failed == 0 else 1)
