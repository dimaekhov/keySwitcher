from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from .config import application_dir

try:
    import winreg
except ImportError:  # pragma: no cover - Windows only
    winreg = None


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "KeySwitcher"


def _ensure_windows() -> None:
    if sys.platform != "win32" or winreg is None:
        raise OSError("Windows startup is supported only on Windows.")


def _preferred_pythonw() -> Path:
    python = Path(sys.executable).resolve()
    candidate = python.with_name("pythonw.exe")
    if candidate.exists():
        return candidate
    return python


def build_startup_command(config_path: str | Path | None = None) -> str:
    app_dir = application_dir()
    if getattr(sys, "frozen", False):
        command = [str(Path(sys.executable).resolve())]
    else:
        command = [str(_preferred_pythonw()), str((app_dir / "keyswitcher" / "__main__.py").resolve())]

    if config_path is not None:
        resolved_config = Path(config_path).expanduser()
        if not resolved_config.is_absolute():
            resolved_config = (app_dir / resolved_config).resolve()
        command.extend(["--config", str(resolved_config)])
    return subprocess.list2cmdline(command)


def get_startup_command() -> str | None:
    _ensure_windows()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return str(value)
    except FileNotFoundError:
        return None


def is_startup_enabled() -> bool:
    return get_startup_command() is not None


def enable_startup(config_path: str | Path | None = None) -> str:
    _ensure_windows()
    command = build_startup_command(config_path)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
        winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, command)
    return command


def disable_startup() -> bool:
    _ensure_windows()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
        return True
    except FileNotFoundError:
        return False
