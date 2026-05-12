import logging

_log = logging.getLogger("hamster_ai.system_usage")


def get_cpu_percent() -> float:
    """Return current CPU usage 0-100. Returns -1.0 if psutil is unavailable."""
    try:
        import psutil
        return psutil.cpu_percent(interval=None)
    except Exception as exc:
        _log.debug(f"cpu_percent error: {exc}")
        return -1.0


def get_ram_percent() -> float:
    """Return current RAM usage 0-100. Returns -1.0 if psutil is unavailable."""
    try:
        import psutil
        return psutil.virtual_memory().percent
    except Exception as exc:
        _log.debug(f"ram_percent error: {exc}")
        return -1.0
