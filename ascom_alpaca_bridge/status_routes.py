from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from .ascom_driver import AscomDriverError, CameraDriver, DomeDriver, FocuserDriver, TelescopeDriver
from .config import AppConfig


DRIVER_BUSY_ERROR_NUMBER = 0x408


def _connected_nowait(driver: TelescopeDriver | DomeDriver | FocuserDriver | CameraDriver) -> bool:
    return driver.connected_nowait()


def _add_connection_error(result: dict[str, Any], device: dict[str, Any], exc: AscomDriverError) -> None:
    device["connected"] = None
    device["error"] = str(exc)
    device["error_number"] = exc.error_number
    if exc.error_number == DRIVER_BUSY_ERROR_NUMBER:
        device["busy"] = True
        return
    result["ok"] = False


def create_status_router(
    config: AppConfig,
    telescope_driver: TelescopeDriver,
    dome_driver: DomeDriver | None = None,
    focuser_driver: FocuserDriver | None = None,
    camera_driver: CameraDriver | None = None,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "server": config.server.server_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @router.get("/status")
    async def status() -> dict[str, Any]:
        result: dict[str, Any] = {
            "ok": True,
            "server": config.server.server_name,
            "telescope": {
                "device_number": config.telescope.device_number,
                "prog_id": config.telescope.prog_id,
                "display_name": config.telescope.display_name,
            },
        }
        try:
            result["telescope"]["connected"] = _connected_nowait(telescope_driver)
        except AscomDriverError as exc:
            _add_connection_error(result, result["telescope"], exc)
        if config.dome.enabled:
            result["dome"] = {
                "device_number": config.dome.device_number,
                "prog_id": config.dome.prog_id,
                "display_name": config.dome.display_name,
            }
            if dome_driver is None:
                result["ok"] = False
                result["dome"]["connected"] = None
                result["dome"]["error"] = "Dome driver is not initialized"
            else:
                try:
                    result["dome"]["connected"] = _connected_nowait(dome_driver)
                except AscomDriverError as exc:
                    _add_connection_error(result, result["dome"], exc)
        if config.focuser.enabled:
            result["focuser"] = {
                "device_number": config.focuser.device_number,
                "prog_id": config.focuser.prog_id,
                "display_name": config.focuser.display_name,
            }
            if focuser_driver is None:
                result["ok"] = False
                result["focuser"]["connected"] = None
                result["focuser"]["error"] = "Focuser driver is not initialized"
            else:
                try:
                    result["focuser"]["connected"] = _connected_nowait(focuser_driver)
                except AscomDriverError as exc:
                    _add_connection_error(result, result["focuser"], exc)
        if config.camera.enabled:
            result["camera"] = {
                "device_number": config.camera.device_number,
                "prog_id": config.camera.prog_id,
                "display_name": config.camera.display_name,
            }
            if camera_driver is None:
                result["ok"] = False
                result["camera"]["connected"] = None
                result["camera"]["error"] = "Camera driver is not initialized"
            else:
                try:
                    result["camera"]["connected"] = _connected_nowait(camera_driver)
                except AscomDriverError as exc:
                    _add_connection_error(result, result["camera"], exc)
        return result

    return router
