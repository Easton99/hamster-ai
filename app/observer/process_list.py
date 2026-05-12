from dataclasses import dataclass

import psutil


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    ram_mb: float
    status: str
    has_network: bool = False


def get_top_processes(n: int = 10) -> list[ProcessInfo]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "status", "cpu_percent", "memory_info"]):
        try:
            info = p.info
            if not info["pid"]:
                continue
            mem_mb = info["memory_info"].rss / 1024 / 1024 if info["memory_info"] else 0
            procs.append(ProcessInfo(
                pid=info["pid"],
                name=info["name"] or "unknown",
                cpu_percent=info["cpu_percent"] or 0.0,
                ram_mb=round(mem_mb, 1),
                status=info["status"] or "unknown",
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda p: p.cpu_percent, reverse=True)
    return procs[:n]


def get_internet_processes() -> list[ProcessInfo]:
    net_pids: set[int] = set()
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "ESTABLISHED" and conn.pid:
                net_pids.add(conn.pid)
    except (psutil.AccessDenied, Exception):
        pass

    procs = []
    for pid in net_pids:
        try:
            p = psutil.Process(pid)
            mem_mb = p.memory_info().rss / 1024 / 1024
            procs.append(ProcessInfo(
                pid=pid,
                name=p.name(),
                cpu_percent=p.cpu_percent(interval=None),
                ram_mb=round(mem_mb, 1),
                status=p.status(),
                has_network=True,
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda p: p.name.lower())
    return procs
