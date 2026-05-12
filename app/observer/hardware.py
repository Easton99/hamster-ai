from dataclasses import dataclass, field


@dataclass
class MonitorInfo:
    index: int
    width: int
    height: int
    is_primary: bool


@dataclass
class UsbDevice:
    name: str
    device_id: str


@dataclass
class BatteryInfo:
    percent: float
    charging: bool
    secsleft: int | None


@dataclass
class HardwareSnapshot:
    monitors: list[MonitorInfo] = field(default_factory=list)
    usb_devices: list[UsbDevice] = field(default_factory=list)
    battery: BatteryInfo | None = None
    internet_reachable: bool | None = None


def get_monitors() -> list[MonitorInfo]:
    try:
        import ctypes
        user32 = ctypes.windll.user32

        monitors = []
        idx = [0]

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_ulong, ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_long), ctypes.c_double
        )

        def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                             ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                             ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            ctypes.windll.user32.GetMonitorInfoW(hMonitor, ctypes.byref(info))
            r = info.rcMonitor
            is_primary = bool(info.dwFlags & 1)
            monitors.append(MonitorInfo(
                index=idx[0],
                width=r.right - r.left,
                height=r.bottom - r.top,
                is_primary=is_primary,
            ))
            idx[0] += 1
            return True

        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
        return monitors
    except Exception:
        return []


def get_usb_devices() -> list[UsbDevice]:
    try:
        import wmi
        c = wmi.WMI()
        devices = []
        for item in c.Win32_USBControllerDevice():
            try:
                dep = item.Dependent
                name = dep.Name or dep.DeviceID or "Unknown USB Device"
                did = dep.DeviceID or ""
                devices.append(UsbDevice(name=name.strip(), device_id=did))
            except Exception:
                continue
        return devices[:20]
    except Exception:
        return []


def get_battery() -> BatteryInfo | None:
    try:
        import psutil
        b = psutil.sensors_battery()
        if b is None:
            return None
        return BatteryInfo(
            percent=round(b.percent, 1),
            charging=b.power_plugged,
            secsleft=b.secsleft if b.secsleft != psutil.POWER_TIME_UNLIMITED else None,
        )
    except Exception:
        return None


def check_internet(target: str = "gateway") -> bool:
    try:
        import socket
        if target == "gateway":
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        return False
    except Exception:
        return False
