from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from .ascom_driver import AscomDriverError, TelescopeDriver
from .config import AppConfig


def create_status_router(config: AppConfig, driver: TelescopeDriver) -> APIRouter:
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
            result["telescope"]["connected"] = bool(driver.get("Connected"))
        except AscomDriverError as exc:
            result["ok"] = False
            result["telescope"]["connected"] = None
            result["telescope"]["error"] = str(exc)
            result["telescope"]["error_number"] = exc.error_number
        return result

    return router
