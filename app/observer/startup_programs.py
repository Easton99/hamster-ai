from dataclasses import dataclass


@dataclass
class StartupEntry:
    name: str
    path: str
    source: str


def get_startup_programs() -> list[StartupEntry]:
    entries = []
    entries.extend(_from_registry(r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU"))
    entries.extend(_from_registry(r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM"))
    entries.extend(_from_startup_folder())
    return entries


def _from_registry(key_path: str, hive: str) -> list[StartupEntry]:
    try:
        import winreg
        root = winreg.HKEY_CURRENT_USER if hive == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        key = winreg.OpenKey(root, key_path)
        entries = []
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                entries.append(StartupEntry(name=name, path=value, source=f"Registry ({hive})"))
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
        return entries
    except Exception:
        return []


def _from_startup_folder() -> list[StartupEntry]:
    try:
        import os
        startup = os.path.expandvars(
            r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
        )
        entries = []
        for f in os.listdir(startup):
            full = os.path.join(startup, f)
            entries.append(StartupEntry(name=f, path=full, source="Startup Folder"))
        return entries
    except Exception:
        return []
