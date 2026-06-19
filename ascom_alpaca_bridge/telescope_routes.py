from __future__ import annotations

import logging
from threading import Thread
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .alpaca_response import empty_response, error_response, value_response
from .ascom_driver import AscomDriverError, TelescopeDriver
from .config import TelescopeConfig


LOG = logging.getLogger(__name__)


GET_PROPERTIES = {
    "name": "Name",
    "description": "Description",
    "driverinfo": "DriverInfo",
    "driverversion": "DriverVersion",
    "interfaceversion": "InterfaceVersion",
    "connected": "Connected",
    "connecting": "Connecting",
    "devicestate": "DeviceState",
    "alignmentmode": "AlignmentMode",
    "rightascension": "RightAscension",
    "declination": "Declination",
    "altitude": "Altitude",
    "aperturearea": "ApertureArea",
    "aperturediameter": "ApertureDiameter",
    "azimuth": "Azimuth",
    "focallength": "FocalLength",
    "ispulseguiding": "IsPulseGuiding",
    "siderealtime": "SiderealTime",
    "slewsettletime": "SlewSettleTime",
    "tracking": "Tracking",
    "slewing": "Slewing",
    "atpark": "AtPark",
    "athome": "AtHome",
    "declinationrate": "DeclinationRate",
    "doesrefraction": "DoesRefraction",
    "equatorialsystem": "EquatorialSystem",
    "guideratedeclination": "GuideRateDeclination",
    "guideraterightascension": "GuideRateRightAscension",
    "rightascensionrate": "RightAscensionRate",
    "siteelevation": "SiteElevation",
    "sitelatitude": "SiteLatitude",
    "sitelongitude": "SiteLongitude",
    "sideofpier": "SideOfPier",
    "targetdeclination": "TargetDeclination",
    "targetrightascension": "TargetRightAscension",
    "trackingrate": "TrackingRate",
    "trackingrates": "TrackingRates",
    "utcdate": "UTCDate",
    "canfindhome": "CanFindHome",
    "canpark": "CanPark",
    "canpulseguide": "CanPulseGuide",
    "cansetdeclinationrate": "CanSetDeclinationRate",
    "cansetguiderates": "CanSetGuideRates",
    "cansetpark": "CanSetPark",
    "cansetpierside": "CanSetPierSide",
    "cansetrightascensionrate": "CanSetRightAscensionRate",
    "cansettracking": "CanSetTracking",
    "canslew": "CanSlew",
    "canslewaltaz": "CanSlewAltAz",
    "canslewaltazasync": "CanSlewAltAzAsync",
    "canslewasync": "CanSlewAsync",
    "cansync": "CanSync",
    "cansyncaltaz": "CanSyncAltAz",
    "canunpark": "CanUnpark",
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
    "canpulseguide",
    "cansetdeclinationrate",
    "cansetguiderates",
    "cansetpark",
    "cansetpierside",
    "cansetrightascensionrate",
    "cansettracking",
    "canslew",
    "canslewaltaz",
    "canslewaltazasync",
    "canslewasync",
    "cansync",
    "cansyncaltaz",
    "canunpark",
}


def _bool_value(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


SET_PROPERTIES = {
    "declinationrate": ("DeclinationRate", float),
    "doesrefraction": ("DoesRefraction", _bool_value),
    "guideratedeclination": ("GuideRateDeclination", float),
    "guideraterightascension": ("GuideRateRightAscension", float),
    "rightascensionrate": ("RightAscensionRate", float),
    "slewsettletime": ("SlewSettleTime", int),
    "siteelevation": ("SiteElevation", float),
    "sitelatitude": ("SiteLatitude", float),
    "sitelongitude": ("SiteLongitude", float),
    "sideofpier": ("SideOfPier", int),
    "targetdeclination": ("TargetDeclination", float),
    "targetrightascension": ("TargetRightAscension", float),
    "trackingrate": ("TrackingRate", int),
    "utcdate": ("UTCDate", str),
}


def _json_error(exc: AscomDriverError, request: Request) -> JSONResponse:
    return JSONResponse(error_response(exc.error_number, str(exc), request))


def _get_form_value(form: dict[str, Any], *names: str) -> Any:
    lowered = {key.lower(): value for key, value in form.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None:
            return value
    raise ValueError(f"Missing required form field: {names[0]}")


def _ok_or_error(request: Request, callback: Any) -> Any:
    try:
        callback()
        return empty_response(request)
    except (ValueError, AscomDriverError) as exc:
        if isinstance(exc, AscomDriverError):
            return _json_error(exc, request)
        return JSONResponse(error_response(0x400, str(exc), request))


def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    count = getattr(value, "Count", None)
    if isinstance(count, int):
        items = []
        for index in range(1, count + 1):
            try:
                items.append(_jsonable(value.Item(index)))
            except Exception:
                try:
                    items.append(_jsonable(value[index - 1]))
                except Exception:
                    break
        return items
    rate_minimum = getattr(value, "Minimum", None)
    rate_maximum = getattr(value, "Maximum", None)
    if rate_minimum is not None and rate_maximum is not None:
        return {"Minimum": rate_minimum, "Maximum": rate_maximum}
    device_state_name = getattr(value, "Name", None)
    device_state_value = getattr(value, "Value", None)
    if device_state_name is not None and device_state_value is not None:
        return {"Name": device_state_name, "Value": _jsonable(device_state_value)}
    try:
        return [_jsonable(item) for item in value]
    except TypeError:
        return str(value)


def _ensure_connected(driver: TelescopeDriver, member: str) -> None:
    if member.lower() in CONNECTED_OPTIONAL_MEMBERS:
        return
    if not bool(driver.get("Connected")):
        raise AscomDriverError(
            f"Telescope must be connected before accessing '{member}'",
            error_number=ALPACA_NOT_CONNECTED,
        )


def _run_telescope_command_background(driver: TelescopeDriver, method_name: str) -> None:
    def worker() -> None:
        try:
            driver.invoke(method_name)
        except AscomDriverError:
            LOG.exception("Telescope %s failed", method_name)

    Thread(target=worker, name=f"telescope-{method_name.lower()}", daemon=True).start()


def create_telescope_router(config: TelescopeConfig, driver: TelescopeDriver) -> APIRouter:
    router = APIRouter(prefix=f"/api/v1/telescope/{config.device_number}")

    @router.get("/supportedactions")
    async def supported_actions(request: Request) -> dict:
        return value_response(SUPPORTED_ACTIONS, request)

    @router.get("/canmoveaxis")
    async def can_move_axis(request: Request) -> Any:
        try:
            _ensure_connected(driver, "canmoveaxis")
            axis = int(request.query_params.get("Axis", request.query_params.get("axis", "")))
            return value_response(driver.invoke("CanMoveAxis", axis), request)
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, "Missing or invalid Axis parameter", request))

    @router.get("/axisrates")
    async def axis_rates(request: Request) -> Any:
        try:
            _ensure_connected(driver, "axisrates")
            axis = int(request.query_params.get("Axis", request.query_params.get("axis", "")))
            return value_response(_jsonable(driver.invoke("AxisRates", axis)), request)
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, "Missing or invalid Axis parameter", request))

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
            return JSONResponse(error_response(0x400, f"Unknown Telescope member: {member}", request))
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

    @router.put("/tracking")
    async def set_tracking(request: Request) -> Any:
        form = dict(await request.form())
        def set_value() -> None:
            tracking = _get_form_value(form, "Tracking")
            driver.set("Tracking", _bool_value(tracking))

        return _ok_or_error(request, set_value)

    @router.put("/slewtocoordinates")
    async def slew_to_coordinates(request: Request) -> Any:
        form = dict(await request.form())
        def invoke() -> None:
            ra = float(_get_form_value(form, "RightAscension"))
            dec = float(_get_form_value(form, "Declination"))
            driver.invoke("SlewToCoordinates", ra, dec)

        return _ok_or_error(request, invoke)

    @router.put("/slewtocoordinatesasync")
    async def slew_to_coordinates_async(request: Request) -> Any:
        form = dict(await request.form())
        def invoke() -> None:
            ra = float(_get_form_value(form, "RightAscension"))
            dec = float(_get_form_value(form, "Declination"))
            driver.invoke("SlewToCoordinatesAsync", ra, dec)

        return _ok_or_error(request, invoke)

    @router.put("/slewtotarget")
    async def slew_to_target(request: Request) -> Any:
        return _ok_or_error(request, lambda: driver.invoke("SlewToTarget"))

    @router.put("/slewtotargetasync")
    async def slew_to_target_async(request: Request) -> Any:
        return _ok_or_error(request, lambda: driver.invoke("SlewToTargetAsync"))

    @router.put("/slewtoaltaz")
    async def slew_to_altaz(request: Request) -> Any:
        form = dict(await request.form())
        def invoke() -> None:
            altitude = float(_get_form_value(form, "Altitude"))
            azimuth = float(_get_form_value(form, "Azimuth"))
            driver.invoke("SlewToAltAz", azimuth, altitude)

        return _ok_or_error(request, invoke)

    @router.put("/slewtoaltazasync")
    async def slew_to_altaz_async(request: Request) -> Any:
        form = dict(await request.form())
        def invoke() -> None:
            altitude = float(_get_form_value(form, "Altitude"))
            azimuth = float(_get_form_value(form, "Azimuth"))
            driver.invoke("SlewToAltAzAsync", azimuth, altitude)

        return _ok_or_error(request, invoke)

    @router.put("/synctocoordinates")
    async def sync_to_coordinates(request: Request) -> Any:
        form = dict(await request.form())
        def invoke() -> None:
            ra = float(_get_form_value(form, "RightAscension"))
            dec = float(_get_form_value(form, "Declination"))
            driver.invoke("SyncToCoordinates", ra, dec)

        return _ok_or_error(request, invoke)

    @router.put("/synctotarget")
    async def sync_to_target(request: Request) -> Any:
        return _ok_or_error(request, lambda: driver.invoke("SyncToTarget"))

    @router.put("/synctoaltaz")
    async def sync_to_altaz(request: Request) -> Any:
        form = dict(await request.form())
        def invoke() -> None:
            altitude = float(_get_form_value(form, "Altitude"))
            azimuth = float(_get_form_value(form, "Azimuth"))
            driver.invoke("SyncToAltAz", azimuth, altitude)

        return _ok_or_error(request, invoke)

    @router.put("/destinationsideofpier")
    async def destination_side_of_pier(request: Request) -> Any:
        form = dict(await request.form())

        try:
            _ensure_connected(driver, "destinationsideofpier")
            ra = float(_get_form_value(form, "RightAscension"))
            dec = float(_get_form_value(form, "Declination"))
            value = driver.invoke("DestinationSideOfPier", ra, dec)
            return value_response(value, request)
        except (ValueError, AscomDriverError) as exc:
            if isinstance(exc, AscomDriverError):
                return _json_error(exc, request)
            return JSONResponse(error_response(0x400, str(exc), request))

    @router.put("/moveaxis")
    async def move_axis(request: Request) -> Any:
        form = dict(await request.form())

        def invoke() -> None:
            axis = int(_get_form_value(form, "Axis"))
            rate = float(_get_form_value(form, "Rate"))
            driver.invoke("MoveAxis", axis, rate)

        return _ok_or_error(request, invoke)

    @router.put("/pulseguide")
    async def pulse_guide(request: Request) -> Any:
        form = dict(await request.form())

        def invoke() -> None:
            direction = int(_get_form_value(form, "Direction"))
            duration = int(_get_form_value(form, "Duration"))
            driver.invoke("PulseGuide", direction, duration)

        return _ok_or_error(request, invoke)

    @router.put("/setpark")
    async def set_park(request: Request) -> Any:
        return _ok_or_error(request, lambda: driver.invoke("SetPark"))

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
        try:
            driver.invoke("AbortSlew")
            return empty_response(request)
        except AscomDriverError as exc:
            return _json_error(exc, request)

    @router.put("/park")
    async def park(request: Request) -> Any:
        _run_telescope_command_background(driver, "Park")
        return empty_response(request)

    @router.put("/unpark")
    async def unpark(request: Request) -> Any:
        _run_telescope_command_background(driver, "Unpark")
        return empty_response(request)

    @router.put("/findhome")
    async def find_home(request: Request) -> Any:
        _run_telescope_command_background(driver, "FindHome")
        return empty_response(request)

    @router.put("/{member}")
    async def set_member(member: str, request: Request) -> Any:
        member_key = member.lower()
        setting = SET_PROPERTIES.get(member_key)
        if setting is None:
            return JSONResponse(error_response(0x400, f"Unknown or read-only Telescope member: {member}", request))

        property_name, converter = setting
        form = dict(await request.form())

        def set_value() -> None:
            value = _get_form_value(form, property_name, member)
            driver.set(property_name, converter(value))

        return _ok_or_error(request, set_value)

    return router
