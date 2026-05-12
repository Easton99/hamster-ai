import threading
import time
from typing import Any

from app.plugins.plugin_base import PluginBase


class Plugin(PluginBase):
    name = "hardware_awareness"
    description = "Monitors, USB devices, battery, and internet status."
    enabled_by_default = False

    def __init__(self) -> None:
        self._app = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._prev_usb: set[str] = set()
        self._warned_low = False
        self._warned_critical = False

    def on_start(self, app: Any) -> None:
        self._app = app
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def on_stop(self, app: Any) -> None:
        self._running = False
        self._app = None

    def on_event(self, event: str, data: Any) -> None:
        pass

    def get_commands(self) -> dict:
        return {
            "/monitors": (self._cmd_monitors, "show connected monitor info"),
            "/usb":      (self._cmd_usb,      "show connected USB devices"),
            "/battery":  (self._cmd_battery,  "show battery status"),
            "/internet": (self._cmd_internet,  "check internet connectivity"),
            "/hardware": (self._cmd_hardware,  "show full hardware summary"),
        }

    # ── Commands ──────────────────────────────────────────────────────────────

    def _cmd_monitors(self, app, args: str) -> str:
        from app.observer.hardware import get_monitors
        monitors = get_monitors()
        if not monitors:
            return "Could not detect monitor information."
        lines = [f"{len(monitors)} monitor(s) connected:"]
        for m in monitors:
            primary = " (primary)" if m.is_primary else ""
            lines.append(f"  Monitor {m.index + 1}: {m.width}×{m.height}{primary}")
        return "\n".join(lines)

    def _cmd_usb(self, app, args: str) -> str:
        from app.observer.hardware import get_usb_devices
        devices = get_usb_devices()
        if not devices:
            return "No USB devices found (wmi may not be installed)."
        lines = [f"{len(devices)} USB device(s):"]
        for d in devices:
            lines.append(f"  {d.name}")
        return "\n".join(lines)

    def _cmd_battery(self, app, args: str) -> str:
        from app.observer.hardware import get_battery
        b = get_battery()
        if b is None:
            return "No battery detected (desktop PC or no battery sensor)."
        status = "Charging" if b.charging else "Discharging"
        if b.secsleft:
            mins = b.secsleft // 60
            time_str = f" — {mins // 60}h {mins % 60}m remaining" if not b.charging else ""
        else:
            time_str = ""
        return f"Battery: {b.percent}% — {status}{time_str}"

    def _cmd_internet(self, app, args: str) -> str:
        from app.observer.hardware import check_internet
        ok = check_internet()
        return "Internet: Connected." if ok else "Internet: Not reachable."

    def _cmd_hardware(self, app, args: str) -> str:
        parts = [
            self._cmd_monitors(app, ""),
            self._cmd_battery(app, ""),
            self._cmd_internet(app, ""),
        ]
        return "\n\n".join(parts)

    # ── Background loop ───────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._check_battery()
                self._check_usb()
            except Exception:
                pass
            time.sleep(60)

    def _check_battery(self) -> None:
        from app.observer.hardware import get_battery
        b = get_battery()
        if b is None or b.charging:
            self._warned_low = False
            self._warned_critical = False
            return
        if b.percent <= 10 and not self._warned_critical:
            self._warned_critical = True
            self._notify(f"Battery critical: {b.percent}% — plug in now.")
        elif b.percent <= 20 and not self._warned_low:
            self._warned_low = True
            self._notify(f"Battery at {b.percent}% and not charging.")

    def _check_usb(self) -> None:
        from app.observer.hardware import get_usb_devices
        devices = get_usb_devices()
        current = {d.name for d in devices}
        added = current - self._prev_usb
        removed = self._prev_usb - current
        for name in added:
            self._notify(f"USB connected: {name}")
        for name in removed:
            self._notify(f"USB removed: {name}")
        self._prev_usb = current

    def _notify(self, msg: str) -> None:
        if self._app:
            try:
                self._app.event_bus.emit("notify", {"title": "Hamster AI", "body": msg})
            except Exception:
                pass


