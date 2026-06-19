from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .alpaca_response import error_response, value_response
from .ascom_driver import AscomDriverError, FocuserDriver
from .config import FocuserConfig
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
    "absolute": "Absolute",
    "ismoving": "IsMoving",
    "maxincrement": "MaxIncrement",
    "maxstep": "MaxStep",
    "position": "Position",
    "stepsize": "StepSize",
    "tempcomp": "TempComp",
    "tempcompavailable": "TempCompAvailable",
    "temperature": "Temperature",
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
    "absolute",
    "maxincrement",
    "maxstep",
    "tempcompavailable",
}


def _ensure_connected(driver: FocuserDriver, member: str) -> None:
    if member.lower() in CONNECTED_OPTIONAL_MEMBERS:
        return
    if not bool(driver.get("Connected")):
        raise AscomDriverError(
            f"Focuser must be connected before accessing '{member}'",
            error_number=ALPACA_NOT_CONNECTED,
        )


def create_focuser_router(config: FocuserConfig, driver: FocuserDriver) -> APIRouter:
    router = APIRouter(prefix=f"/api/v1/focuser/{config.device_number}")

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
            return JSONResponse(error_response(0x400, f"Unknown Focuser member: {member}", request))
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

    @router.put("/tempcomp")
    async def set_tempcomp(request: Request) -> Any:
        form = dict(await request.form())

        def set_value() -> None:
            _ensure_connected(driver, "tempcomp")
            temp_comp = _get_form_value(form, "TempComp")
            driver.set("TempComp", _bool_value(temp_comp))

        return _ok_or_error(request, set_value)

    @router.put("/halt")
    async def halt(request: Request) -> Any:
        return _ok_or_error(request, lambda: (_ensure_connected(driver, "halt"), driver.invoke("Halt")))

    @router.put("/move")
    async def move(request: Request) -> Any:
        form = dict(await request.form())

        def invoke() -> None:
            _ensure_connected(driver, "move")
            position = int(_get_form_value(form, "Position"))
            driver.invoke("Move", position)

        return _ok_or_error(request, invoke)

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

    return router
