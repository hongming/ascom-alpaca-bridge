from __future__ import annotations

from fastapi import APIRouter, Request

from .alpaca_response import value_response
from .config import AppConfig


def create_management_router(config: AppConfig) -> APIRouter:
    router = APIRouter()

    @router.get("/management/apiversions")
    def api_versions(request: Request) -> dict:
        return value_response([1], request)

    @router.get("/management/v1/description")
    def description(request: Request) -> dict:
        return value_response(
            {
                "ServerName": config.server.server_name,
                "Manufacturer": config.server.manufacturer,
                "ManufacturerVersion": config.server.manufacturer_version,
                "Location": config.server.location,
            },
            request,
        )

    @router.get("/management/v1/configureddevices")
    def configured_devices(request: Request) -> dict:
        return value_response(
            [
                {
                    "DeviceName": config.telescope.display_name,
                    "DeviceType": "Telescope",
                    "DeviceNumber": config.telescope.device_number,
                    "UniqueID": config.telescope.unique_id,
                }
            ],
            request,
        )

    return router
