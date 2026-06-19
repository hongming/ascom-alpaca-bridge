from __future__ import annotations

import platform

from .ascom_driver import AscomDriverError


def choose_device(device_type: str, previous_prog_id: str = "") -> str:
    if platform.system() != "Windows":
        raise AscomDriverError("ASCOM Chooser is only available on Windows")

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise AscomDriverError("pywin32 is required to use ASCOM Chooser") from exc

    pythoncom.CoInitialize()
    try:
        chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
        chooser.DeviceType = device_type
        selected = chooser.Choose(previous_prog_id or "")
    except Exception as exc:
        raise AscomDriverError(f"Unable to open ASCOM {device_type} Chooser: {exc}") from exc

    if selected is None:
        return ""
    return str(selected).strip()


def choose_telescope(previous_prog_id: str = "") -> str:
    return choose_device("Telescope", previous_prog_id)


def choose_dome(previous_prog_id: str = "") -> str:
    return choose_device("Dome", previous_prog_id)


def choose_focuser(previous_prog_id: str = "") -> str:
    return choose_device("Focuser", previous_prog_id)


def choose_camera(previous_prog_id: str = "") -> str:
    return choose_device("Camera", previous_prog_id)
