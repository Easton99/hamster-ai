from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.core.app_context import AppContext

CommandHandler = Callable[["AppContext", str], str]


class CommandDispatcher:
    def __init__(self) -> None:
        self._commands: dict[str, CommandHandler] = {}
        self._descriptions: dict[str, str] = {}

    def register(self, name: str, handler: CommandHandler, description: str = "") -> None:
        key = name.lstrip("/").lower()
        self._commands[key] = handler
        self._descriptions[key] = description

    def is_command(self, text: str) -> bool:
        return text.startswith("/")

    def dispatch(self, raw: str, app: "AppContext") -> str:
        parts = raw.lstrip("/").split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""
        handler = self._commands.get(cmd)
        if handler is None:
            return f"Unknown command: /{cmd}\nType /help for available commands."
        try:
            return handler(app, args)
        except Exception as exc:
            app.logger.error(f"Command /{cmd} error: {exc}", exc_info=True)
            return f"Command error: {exc}"

    def unregister(self, name: str) -> None:
        key = name.lstrip("/").lower()
        self._commands.pop(key, None)
        self._descriptions.pop(key, None)

    def list_commands(self) -> list[tuple[str, str]]:
        return [(cmd, self._descriptions.get(cmd, "")) for cmd in sorted(self._commands)]

    def get_help(self) -> str:
        lines = ["Available commands:"]
        for cmd in sorted(self._commands):
            desc = self._descriptions.get(cmd, "")
            suffix = f" — {desc}" if desc else ""
            lines.append(f"  /{cmd}{suffix}")
        return "\n".join(lines)


# ── Command handlers ──────────────────────────────────────────────────────────

def _remember(app: "AppContext", args: str) -> str:
    if not args:
        return "Usage: /remember <something>"
    m = app.store.add_memory(args)
    return f"Got it. Saved as memory #{m.id}."


def _todo(app: "AppContext", args: str) -> str:
    if not args:
        return "Usage: /todo <task>"
    t = app.store.add_todo(args)
    return f"Todo added (#{t.id}): {t.text}"


def _note(app: "AppContext", args: str) -> str:
    if not args:
        return "Usage: /note <text>"
    n = app.store.add_note(args)
    return f"Note saved (#{n.id})."


def _show_todos(app: "AppContext", args: str) -> str:
    todos = app.store.list_todos()
    if not todos:
        return "No open todos."
    lines = ["Open todos:"]
    for t in todos:
        suffix = f" ({t.due_date})" if t.due_date else ""
        lines.append(f"  #{t.id} {t.text}{suffix}")
    return "\n".join(lines)


def _show_notes(app: "AppContext", args: str) -> str:
    notes = app.store.list_notes()
    if not notes:
        return "No notes."
    lines = ["Notes:"]
    for n in notes:
        lines.append(f"  #{n.id} [{n.created_at[:10]}] {n.text}")
    return "\n".join(lines)


def _show_memories(app: "AppContext", args: str) -> str:
    tag = args.strip().lstrip("#") if args.strip() else None
    memories = app.store.list_memories(tag=tag)
    if not memories:
        qualifier = f" tagged #{tag}" if tag else ""
        return f"No memories{qualifier}."
    qualifier = f" tagged #{tag}" if tag else ""
    lines = [f"Memories{qualifier}:"]
    for m in memories:
        tags = f" [{m.tags}]" if m.tags else ""
        lines.append(f"  #{m.id} [{m.type}]{tags} {m.content}")
    return "\n".join(lines)


def _forget(app: "AppContext", args: str) -> str:
    if not args:
        return "Usage: /forget <id>  (see /show-memories for IDs)"
    try:
        mid = int(args.lstrip("#"))
    except ValueError:
        return "Usage: /forget <id>  (must be a number)"
    return f"Memory #{mid} deleted." if app.store.delete_memory(mid) else f"No memory with id #{mid}."


def _done(app: "AppContext", args: str) -> str:
    if not args:
        return "Usage: /done <id>  (see /show-todos for IDs)"
    try:
        tid = int(args.lstrip("#"))
    except ValueError:
        return "Usage: /done <id>  (must be a number)"
    return f"Todo #{tid} marked done." if app.store.complete_todo(tid) else f"No todo with id #{tid}."


def _show_features(app: "AppContext", args: str) -> str:
    features = app.store.list_features()
    if not features:
        return "No feature requests yet."
    lines = ["Feature requests:"]
    for f in features:
        lines.append(f"  #{f.id} [{f.status}] {f.title}")
    return "\n".join(lines)


def _add_feature(app: "AppContext", args: str) -> str:
    if not args:
        return "Usage: /add-feature <title>"
    feat = app.store.add_feature(args)
    return f"Feature request added (#{feat.id}): {feat.title}"


def _feature_planned(app: "AppContext", args: str) -> str:
    try:
        fid = int(args.lstrip("#"))
        return f"Feature #{fid} marked planned." if app.store.update_feature_status(fid, "planned") else f"Feature #{fid} not found."
    except ValueError:
        return "Usage: /feature-planned <id>"


def _feature_done(app: "AppContext", args: str) -> str:
    try:
        fid = int(args.lstrip("#"))
        return f"Feature #{fid} marked done." if app.store.update_feature_status(fid, "done") else f"Feature #{fid} not found."
    except ValueError:
        return "Usage: /feature-done <id>"


def _delete_feature(app: "AppContext", args: str) -> str:
    try:
        fid = int(args.lstrip("#"))
        return f"Feature #{fid} deleted." if app.store.delete_feature(fid) else f"Feature #{fid} not found."
    except ValueError:
        return "Usage: /delete-feature <id>"


def _status(app: "AppContext", args: str) -> str:
    lines = [
        f"Model      : {app.settings.get('model')}",
        f"Personality: {app.settings.get('personality')}",
        f"Log level  : {app.settings.get('log_level')}",
    ]
    if app.modes:
        active = app.modes.active_modes()
        lines.append(f"Modes      : {', '.join(active) if active else 'none'}")
    if app.plugin_manager:
        plugins = app.plugin_manager.list_plugins()
        active_p = [p["name"] for p in plugins if p["enabled"]]
        lines.append(f"Plugins    : {', '.join(active_p) if active_p else 'none'}")
    return "\n".join(lines)


# ── Mode commands ─────────────────────────────────────────────────────────────

def _focus(app: "AppContext", args: str) -> str:
    if not app.modes:
        return "Mode manager not available."
    minutes: float | None = None
    if args:
        arg = args.strip().lower()
        try:
            if arg.endswith("h"):
                minutes = float(arg[:-1]) * 60
            else:
                minutes = float(arg.rstrip("m"))
        except ValueError:
            return "Usage: /focus <minutes> or /focus <Nh>  e.g. /focus 30 or /focus 1h"
    else:
        minutes = 30.0
    app.modes.enable_focus_mode(minutes)
    label = f"{int(minutes)}m" if minutes < 60 else f"{minutes/60:.4g}h"
    return f"Focus Mode on for {label}. Use /resume to end early."


def _quiet(app: "AppContext", args: str) -> str:
    if not app.modes:
        return "Mode manager not available."
    app.modes.enable_focus_mode(minutes=None)
    return "Focus Mode on (no timer). Use /resume to end."


def _resume(app: "AppContext", args: str) -> str:
    if not app.modes:
        return "Mode manager not available."
    if not app.modes.focus_mode:
        return "Focus Mode is not active."
    app.modes.disable_focus_mode()
    return "Focus Mode off. Back to normal."


def _private_on(app: "AppContext", args: str) -> str:
    if not app.modes:
        return "Mode manager not available."
    app.modes.enable_private_mode()
    return "Private Mode on. Nothing will be logged or stored."


def _private_off(app: "AppContext", args: str) -> str:
    if not app.modes:
        return "Mode manager not available."
    if not app.modes.private_mode:
        return "Private Mode is not active."
    app.modes.disable_private_mode()
    return "Private Mode off."


# ── Forget Mode commands ──────────────────────────────────────────────────────

def _forget_last_hour(app: "AppContext", args: str) -> str:
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    n_mem = app.store.delete_memories_since(cutoff)
    n_note = app.store.delete_notes_since(cutoff)
    n_todo = app.store.delete_todos_since(cutoff)
    n_sess = app.store.delete_sessions_since(cutoff)
    return f"Cleared last hour: {n_mem} memories, {n_note} notes, {n_todo} todos, {n_sess} sessions."


def _forget_today(app: "AppContext", args: str) -> str:
    from datetime import date
    cutoff = date.today().strftime("%Y-%m-%d") + " 00:00:00"
    n_mem = app.store.delete_memories_since(cutoff)
    n_note = app.store.delete_notes_since(cutoff)
    n_todo = app.store.delete_todos_since(cutoff)
    n_sess = app.store.delete_sessions_since(cutoff)
    return f"Cleared today: {n_mem} memories, {n_note} notes, {n_todo} todos, {n_sess} sessions."


def _forget_session(app: "AppContext", args: str) -> str:
    # Chat history lives in the window — signal it via event bus
    app.event_bus.emit("forget_session")
    return "Session cleared."


def _forget_private(app: "AppContext", args: str) -> str:
    n = app.store.delete_memories_since("1970-01-01 00:00:00")
    return f"All memories cleared ({n} removed)."


def _clear_activity(app: "AppContext", args: str) -> str:
    n = app.store.delete_sessions_since("1970-01-01 00:00:00")
    return f"Activity log cleared ({n} sessions removed)."


def _health(app: "AppContext", args: str) -> str:
    if not app.diagnostics:
        return "Diagnostics not available."
    results = app.diagnostics.run_checks()
    lines = []
    for r in results:
        icon = {"ok": "✓", "warning": "!", "fail": "✗"}.get(r.status, "?")
        lines.append(f"  {icon} {r.name}: {r.message}")
    return "\n".join(lines)


def _errors(app: "AppContext", args: str) -> str:
    if not app.diagnostics:
        return "Diagnostics not available."
    errors = app.diagnostics.recent_errors(10)
    return "\n".join(errors) if errors else "No recent errors."


def _fix(app: "AppContext", args: str) -> str:
    if not app.diagnostics:
        return "Diagnostics not available."
    results = app.diagnostics.run_checks()
    suggestions = app.diagnostics.suggestions_for(results)
    if not suggestions:
        return "No fixes needed — everything looks good."
    lines = ["Suggested fixes (use /fix <key> to apply):"]
    for s in suggestions:
        lines.append(f"  {s.key} — {s.label}")
    if args.strip():
        ok, msg = app.diagnostics.apply_fix(args.strip())
        return f"Fix '{args.strip()}': {'OK' if ok else 'FAILED'} — {msg}"
    return "\n".join(lines)


def _help(app: "AppContext", args: str) -> str:
    return app.commands.get_help()


# ── Model commands ────────────────────────────────────────────────────────────

def _model(app: "AppContext", args: str) -> str:
    mm = app.model_manager
    if not mm:
        return "Model manager not available."
    sub = args.strip().lower()
    if not sub:
        return f"Current model: {mm.current()}"
    if sub == "list":
        models = mm.list_available()
        if not models:
            return "No models found — is Ollama running?"
        return "Available models:\n" + "\n".join(f"  {m}" for m in models)
    if sub.startswith("use "):
        name = sub[4:].strip()
        if not name:
            return "Usage: /model use <name>"
        mm.switch(name)
        app.settings.set("model", name)
        return f"Switched to model: {name}"
    return "Usage: /model | /model list | /model use <name>"


# ── Memory search / tag commands ──────────────────────────────────────────────

def _search_memory(app: "AppContext", args: str) -> str:
    if not args:
        return "Usage: /search-memory <keyword>"
    results = app.store.search_memories(args)
    if not results:
        return f"No memories matching '{args}'."
    lines = [f"Found {len(results)} memories matching '{args}':"]
    for m in results:
        tags = f" [{m.tags}]" if m.tags else ""
        lines.append(f"  #{m.id} [{m.created_at[:10]}]{tags} {m.content}")
    return "\n".join(lines)


def _search_notes(app: "AppContext", args: str) -> str:
    if not args:
        return "Usage: /search-notes <keyword>"
    from app.memory.search import search_notes
    results = search_notes(app.db, args)
    if not results:
        return f"No notes matching '{args}'."
    lines = [f"Found {len(results)} notes:"]
    for n in results:
        lines.append(f"  #{n['id']} [{n['created_at'][:10]}] {n['text']}")
    return "\n".join(lines)


def _search_todos(app: "AppContext", args: str) -> str:
    if not args:
        return "Usage: /search-todos <keyword>"
    from app.memory.search import search_todos
    results = search_todos(app.db, args)
    if not results:
        return f"No todos matching '{args}'."
    lines = [f"Found {len(results)} todos:"]
    for t in results:
        done = " [done]" if t.get("done") else ""
        lines.append(f"  #{t['id']}{done} {t['text']}")
    return "\n".join(lines)


def _tag_memory(app: "AppContext", args: str) -> str:
    parts = args.strip().split(" ", 1)
    if len(parts) != 2:
        return "Usage: /tag-memory <id> <tag>"
    try:
        mid = int(parts[0].lstrip("#"))
    except ValueError:
        return "Usage: /tag-memory <id> <tag>  (id must be a number)"
    tag = parts[1].strip().lstrip("#")
    ok = app.store.tag_memory(mid, tag)
    return f"Memory #{mid} tagged with '{tag}'." if ok else f"No memory with id #{mid}."


# ── Factory ───────────────────────────────────────────────────────────────────

def build_dispatcher() -> CommandDispatcher:
    d = CommandDispatcher()
    # Memory
    d.register("/remember",         _remember,         "save a memory")
    d.register("/todo",             _todo,             "add a todo item")
    d.register("/note",             _note,             "save a quick note")
    d.register("/show-todos",       _show_todos,       "list open todos")
    d.register("/show-notes",       _show_notes,       "list all notes")
    d.register("/show-memories",    _show_memories,    "list all memories")
    d.register("/forget",           _forget,           "delete a memory by id")
    d.register("/done",             _done,             "mark a todo as done")
    # Features
    d.register("/show-features",    _show_features,    "list feature requests")
    d.register("/add-feature",      _add_feature,      "add a feature request")
    d.register("/feature-planned",  _feature_planned,  "mark feature as planned")
    d.register("/feature-done",     _feature_done,     "mark feature as done")
    d.register("/delete-feature",   _delete_feature,   "delete a feature request")
    # Modes
    d.register("/focus",            _focus,            "enable Focus Mode (minutes or Nh)")
    d.register("/quiet",            _quiet,            "enable Focus Mode indefinitely")
    d.register("/resume",           _resume,           "end Focus Mode")
    d.register("/private",          _private_on,       "enable Private Mode")
    d.register("/private-off",      _private_off,      "disable Private Mode")
    # Forget
    d.register("/forget-last-hour", _forget_last_hour, "delete data from the last hour")
    d.register("/forget-today",     _forget_today,     "delete data from today")
    d.register("/forget-session",   _forget_session,   "clear current chat session")
    d.register("/forget-private",   _forget_private,   "clear all memories")
    d.register("/clear-activity",   _clear_activity,   "clear activity log")
    # Diagnostics
    d.register("/health",           _health,           "run health checks")
    d.register("/errors",           _errors,           "show recent errors")
    d.register("/fix",              _fix,              "show or apply self-fix suggestions")
    # Model
    d.register("/model",            _model,            "show/switch Ollama model")
    # Memory search & tags
    d.register("/search-memory",    _search_memory,    "search memories by keyword")
    d.register("/search-notes",     _search_notes,     "search notes by keyword")
    d.register("/search-todos",     _search_todos,     "search todos by keyword")
    d.register("/tag-memory",       _tag_memory,       "tag a memory by id")
    # System
    d.register("/status",           _status,           "show app status")
    d.register("/help",             _help,             "list all commands")
    return d
