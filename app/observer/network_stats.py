import time
from dataclasses import dataclass, field

import psutil


@dataclass
class NetworkSnapshot:
    bytes_sent: int = 0
    bytes_recv: int = 0
    sent_rate_kbps: float = 0.0
    recv_rate_kbps: float = 0.0


class NetworkStatsTracker:
    def __init__(self) -> None:
        c = psutil.net_io_counters()
        self._prev_sent = c.bytes_sent
        self._prev_recv = c.bytes_recv
        self._prev_time = time.monotonic()

    def snapshot(self) -> NetworkSnapshot:
        c = psutil.net_io_counters()
        now = time.monotonic()
        elapsed = max(now - self._prev_time, 0.001)

        sent_rate = (c.bytes_sent - self._prev_sent) / elapsed / 1024
        recv_rate = (c.bytes_recv - self._prev_recv) / elapsed / 1024

        self._prev_sent = c.bytes_sent
        self._prev_recv = c.bytes_recv
        self._prev_time = now

        return NetworkSnapshot(
            bytes_sent=c.bytes_sent,
            bytes_recv=c.bytes_recv,
            sent_rate_kbps=round(sent_rate, 1),
            recv_rate_kbps=round(recv_rate, 1),
        )
