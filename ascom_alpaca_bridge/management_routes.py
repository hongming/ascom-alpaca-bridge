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
        devices = [
            {
                "DeviceName": config.telescope.display_name,
                "DeviceType": "Telescope",
                "DeviceNumber": config.telescope.device_number,
                "UniqueID": config.telescope.unique_id,
            }
        ]
        if config.dome.enabled:
            devices.append(
                {
                    "DeviceName": config.dome.display_name,
                    "DeviceType": "Dome",
                    "DeviceNumber": config.dome.device_number,
                    "UniqueID": config.dome.unique_id,
                }
            )
        if config.focuser.enabled:
            devices.append(
                {
                    "DeviceName": config.focuser.display_name,
                    "DeviceType": "Focuser",
                    "DeviceNumber": config.focuser.device_number,
                    "UniqueID": config.focuser.unique_id,
                }
            )
        if config.camera.enabled:
            devices.append(
                {
                    "DeviceName": config.camera.display_name,
                    "DeviceType": "Camera",
                    "DeviceNumber": config.camera.device_number,
                    "UniqueID": config.camera.unique_id,
                }
            )
        return value_response(devices, request)

    return router
