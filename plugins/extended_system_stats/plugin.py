import threading
import time
from typing import Any

import psutil

from app.plugins.plugin_base import PluginBase


class Plugin(PluginBase):
    name = "extended_system_stats"
    description = "GPU, per-process CPU/RAM, disk usage, and network bandwidth."
    enabled_by_default = False

    def __init__(self) -> None:
        self._app = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._snapshot: dict = {}
        self._net_tracker = None

    def on_start(self, app: Any) -> None:
        self._app = app
        from app.observer.network_stats import NetworkStatsTracker
        self._net_tracker = NetworkStatsTracker()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def on_stop(self, app: Any) -> None:
        self._running = False

    def on_event(self, event: str, data: Any) -> None:
        pass

    def get_commands(self) -> dict:
        return {
            "/system":       (self._cmd_system,       "show system stats snapshot"),
            "/top-processes":(self._cmd_top_procs,    "show top CPU/RAM processes"),
            "/disk":         (self._cmd_disk,          "show disk usage"),
            "/network":      (self._cmd_network,       "show network usage"),
            "/gpu":          (self._cmd_gpu,           "show GPU usage and temperature"),
        }

    def get_snapshot(self) -> dict:
        return dict(self._snapshot)

    # ── Commands ──────────────────────────────────────────────────────────────

    def _cmd_system(self, app, args: str) -> str:
        s = self._snapshot
        if not s:
            return "No snapshot available yet — wait a moment."
        lines = [
            f"CPU:     {s.get('cpu_percent', '?')}%",
            f"RAM:     {s.get('ram_percent', '?')}% ({s.get('ram_used_gb', '?')} GB / {s.get('ram_total_gb', '?')} GB)",
        ]
        if s.get("gpus"):
            for g in s["gpus"]:
                temp = f" | {g['temp']}°C" if g.get("temp") is not None else ""
                lines.append(f"GPU:     {g['name']} — {g['load']}%{temp}")
        if s.get("disks"):
            for d in s["disks"]:
                lines.append(f"Disk {d['mount']}: {d['used_gb']} / {d['total_gb']} GB ({d['percent']}%)")
        if s.get("net"):
            n = s["net"]
            lines.append(f"Network: ↑{n['sent_kbps']} KB/s  ↓{n['recv_kbps']} KB/s")
        return "\n".join(lines)

    def _cmd_top_procs(self, app, args: str) -> str:
        from app.observer.process_list import get_top_processes
        procs = get_top_processes(8)
        if not procs:
            return "No process data available."
        lines = ["Top processes by CPU:"]
        for p in procs:
            lines.append(f"  {p.name:<30} CPU: {p.cpu_percent:>5.1f}%  RAM: {p.ram_mb:.0f} MB")
        return "\n".join(lines)

    def _cmd_disk(self, app, args: str) -> str:
        disks = self._snapshot.get("disks", [])
        if not disks:
            return "No disk data available."
        lines = ["Disk usage:"]
        for d in disks:
            lines.append(f"  {d['mount']}: {d['used_gb']} / {d['total_gb']} GB — {d['percent']}% used")
        return "\n".join(lines)

    def _cmd_network(self, app, args: str) -> str:
        n = self._snapshot.get("net")
        if not n:
            return "No network data yet."
        return (
            f"Network I/O:\n"
            f"  Upload:   {n['sent_kbps']} KB/s\n"
            f"  Download: {n['recv_kbps']} KB/s"
        )

    def _cmd_gpu(self, app, args: str) -> str:
        gpus = self._snapshot.get("gpus", [])
        if not gpus:
            return "No GPU data available. GPUtil or pyamdgpuinfo may not be installed."
        lines = ["GPU status:"]
        for g in gpus:
            temp = f"{g['temp']}°C" if g.get("temp") is not None else "N/A"
            lines.append(
                f"  {g['name']}: {g['load']}% load | "
                f"{g['mem_used']} / {g['mem_total']} MB VRAM | {temp}"
            )
        return "\n".join(lines)

    # ── Poll loop ─────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        from app.observer.gpu import get_gpu_stats

        interval = 30
        while self._running:
            try:
                self._collect(get_gpu_stats)
            except Exception:
                pass
            time.sleep(interval)

    def _collect(self, get_gpu_stats) -> None:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        gpus_raw = get_gpu_stats()

        disks = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "mount": part.mountpoint,
                    "used_gb": round(usage.used / 1e9, 1),
                    "total_gb": round(usage.total / 1e9, 1),
                    "percent": usage.percent,
                })
            except Exception:
                continue

        net = None
        if self._net_tracker:
            snap = self._net_tracker.snapshot()
            net = {"sent_kbps": snap.sent_rate_kbps, "recv_kbps": snap.recv_rate_kbps}

        gpus = [
            {
                "name": g.name,
                "load": g.load_percent,
                "mem_used": g.memory_used_mb,
                "mem_total": g.memory_total_mb,
                "temp": g.temperature_c,
            }
            for g in gpus_raw
        ]

        self._snapshot = {
            "cpu_percent": cpu,
            "ram_percent": ram.percent,
            "ram_used_gb": round(ram.used / 1e9, 1),
            "ram_total_gb": round(ram.total / 1e9, 1),
            "disks": disks,
            "net": net,
            "gpus": gpus,
        }

        self._check_warnings(cpu, ram.percent, disks, gpus)

    def _check_warnings(self, cpu, ram_pct, disks, gpus) -> None:
        if not self._app:
            return
        if cpu > 90:
            self._notify(f"CPU is at {cpu}%.")
        if ram_pct > 90:
            self._notify(f"RAM usage is at {ram_pct}%.")
        for d in disks:
            if d["percent"] > 90:
                self._notify(f"Disk {d['mount']} is {d['percent']}% full.")
        for g in gpus:
            if g.get("temp") and g["temp"] > 85:
                self._notify(f"GPU temperature is {g['temp']}°C.")

    def _notify(self, msg: str) -> None:
        try:
            self._app.event_bus.emit("notify", {"title": "Hamster AI", "body": msg})
        except Exception:
            pass


