from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .alpaca_response import empty_response, error_response, value_response
from .ascom_driver import AscomDriverError, DomeDriver
from .config import DomeConfig
from .telescope_routes import _bool_value, _get_form_value, _json_error, _jsonable, _ok_or_error


GET_PROPERTIES = {
    "name": "Name",
    "description": "Description",
    "driverinfo": "DriverInfo",
    "driverversion": "DriverVersion",
    "interfaceversion": "InterfaceVersion",
    "connected": "Connected",
    "connecting": "Connecting",
    "devicestate": "DeviceState",
    "altitude": "Altitude",
    "athome": "AtHome",
    "atpark": "AtPark",
    "azimuth": "Azimuth",
    "canfindhome": "CanFindHome",
    "canpark": "CanPark",
    "cansetaltitude": "CanSetAltitude",
    "cansetazimuth": "CanSetAzimuth",
    "cansetpark": "CanSetPark",
    "cansetshutter": "CanSetShutter",
    "canslave": "CanSlave",
    "cansyncazimuth": "CanSyncAzimuth",
    "shutterstatus": "ShutterStatus",
    "slaved": "Slaved",
    "slewing": "Slewing",
}

SUPPORTED_ACTIONS: list[str] = []
ALPACA_NOT_CONNECTED = 0x407

CONNECTED_OPTIONAL_MEMBERS = {
    "name",
    "description",
    "driverinfo",
    "driverversion",
    "interfaceversion",
    "connected",
    "connecting",
    "devicestate",
    "supportedactions",
    "canfindhome",
    "canpark",
    "cansetaltitude",
    "cansetazimuth",
    "cansetpark",
    "cansetshutter",
    "canslave",
    "cansyncazimuth",
}


def _ensure_connected(driver: DomeDriver, member: str) -> None:
    if member.lower() in CONNECTED_OPTIONAL_MEMBERS:
        return
    if not bool(driver.get("Connected")):
        raise AscomDriverError(
            f"Dome must be connected before accessing '{member}'",
            error_number=ALPACA_NOT_CONNECTED,
        )


def create_dome_router(config: DomeConfig, driver: DomeDriver) -> APIRouter:
    router = APIRouter(prefix=f"/api/v1/dome/{config.device_number}")

    @router.get("/supportedactions")
    async def supported_actions(request: Request) -> dict:
        return value_response(SUPPORTED_ACTIONS, request)

    @router.get("/connecting")
    async def connecting(request: Request) -> Any:
        try:
            return value_response(bool(driver.get("Connecting")), request)
        except AscomDriverError:
            return value_response(False, request)

    @router.get("/{member}")
    async def get_member(member: str, request: Request) -> Any:
        property_name = GET_PROPERTIES.get(member.lower())
        if property_name is None:
            return JSONResponse(error_response(0x400, f"Unknown Dome member: {member}", request))
        try:
            _ensure_connected(driver, member)
            return value_response(_jsonable(driver.get(property_name)), request)
        except AscomDriverError as exc:
            return _json_error(exc, request)

    @router.put("/connected")
    async def set_connected(request: Request) -> Any:
        form = dict(await request.form())

        def set_value() -> None:
            connected = _get_form_value(form, "Connected")
            driver.set("Connected", _bool_value(connected))

        return _ok_or_error(request, set_value)

    @router.put("/connect")
    async def connect(request: Request) -> Any:
        return _ok_or_error(request, lambda: driver.set("Connected", True))

    @router.put("/disconnect")
    async def disconnect(request: Request) -> Any:
        return _ok_or_error(request, lambda: driver.set("Connected", False))

    @router.put("/slaved")
    async def set_slaved(request: Request) -> Any:
        form = dict(await request.form())

        def set_value() -> None:
            _ensure_connected(driver, "slaved")
            slaved = _get_form_value(form, "Slaved")
            driver.set("Slaved", _bool_value(slaved))

        return _ok_or_error(request, set_value)

    @router.put("/action")
    async def action(request: Request) -> Any:
        form = dict(await request.form())
        try:
            action_name = str(_get_form_value(form, "Action"))
            parameters = str(_get_form_value(form, "Parameters"))
            _ensure_connected(driver, "action")
            return value_response(_jsonable(driver.invoke("Action", action_name, parameters)), request)
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, str(exc), request))

    @router.put("/commandblind")
    async def command_blind(request: Request) -> Any:
        form = dict(await request.form())

        def invoke() -> None:
            command = str(_get_form_value(form, "Command"))
            raw = _bool_value(_get_form_value(form, "Raw"))
            _ensure_connected(driver, "commandblind")
            driver.invoke("CommandBlind", command, raw)

        return _ok_or_error(request, invoke)

    @router.put("/commandbool")
    async def command_bool(request: Request) -> Any:
        form = dict(await request.form())
        try:
            command = str(_get_form_value(form, "Command"))
            raw = _bool_value(_get_form_value(form, "Raw"))
            _ensure_connected(driver, "commandbool")
            return value_response(bool(driver.invoke("CommandBool", command, raw)), request)
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, str(exc), request))

    @router.put("/commandstring")
    async def command_string(request: Request) -> Any:
        form = dict(await request.form())
        try:
            command = str(_get_form_value(form, "Command"))
            raw = _bool_value(_get_form_value(form, "Raw"))
            _ensure_connected(driver, "commandstring")
            return value_response(str(driver.invoke("CommandString", command, raw)), request)
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, str(exc), request))

    @router.put("/abortslew")
    async def abort_slew(request: Request) -> Any:
        return _ok_or_error(request, lambda: (_ensure_connected(driver, "abortslew"), driver.invoke("AbortSlew")))

    @router.put("/closeshutter")
    async def close_shutter(request: Request) -> Any:
        return _ok_or_error(request, lambda: (_ensure_connected(driver, "closeshutter"), driver.invoke("CloseShutter")))

    @router.put("/findhome")
    async def find_home(request: Request) -> Any:
        return _ok_or_error(request, lambda: (_ensure_connected(driver, "findhome"), driver.invoke("FindHome")))

    @router.put("/openshutter")
    async def open_shutter(request: Request) -> Any:
        return _ok_or_error(request, lambda: (_ensure_connected(driver, "openshutter"), driver.invoke("OpenShutter")))

    @router.put("/park")
    async def park(request: Request) -> Any:
        return _ok_or_error(request, lambda: (_ensure_connected(driver, "park"), driver.invoke("Park")))

    @router.put("/setpark")
    async def set_park(request: Request) -> Any:
        return _ok_or_error(request, lambda: (_ensure_connected(driver, "setpark"), driver.invoke("SetPark")))

    @router.put("/slewtoaltitude")
    async def slew_to_altitude(request: Request) -> Any:
        form = dict(await request.form())

        def invoke() -> None:
            _ensure_connected(driver, "slewtoaltitude")
            altitude = float(_get_form_value(form, "Altitude"))
            driver.invoke("SlewToAltitude", altitude)

        return _ok_or_error(request, invoke)

    @router.put("/slewtoazimuth")
    async def slew_to_azimuth(request: Request) -> Any:
        form = dict(await request.form())

        def invoke() -> None:
            _ensure_connected(driver, "slewtoazimuth")
            azimuth = float(_get_form_value(form, "Azimuth"))
            driver.invoke("SlewToAzimuth", azimuth)

        return _ok_or_error(request, invoke)

    @router.put("/synctoazimuth")
    async def sync_to_azimuth(request: Request) -> Any:
        form = dict(await request.form())

        def invoke() -> None:
            _ensure_connected(driver, "synctoazimuth")
            azimuth = float(_get_form_value(form, "Azimuth"))
            driver.invoke("SyncToAzimuth", azimuth)

        return _ok_or_error(request, invoke)

    return router
