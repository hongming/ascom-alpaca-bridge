from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    data: dict[str, str] | None = None
    safe: bool = True


SAFE_GET_ENDPOINTS = [
    "connected",
    "connecting",
    "name",
    "description",
    "driverinfo",
    "driverversion",
    "interfaceversion",
    "supportedactions",
    "alignmentmode",
    "altitude",
    "aperturearea",
    "aperturediameter",
    "athome",
    "atpark",
    "azimuth",
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
    "declination",
    "declinationrate",
    "devicestate",
    "doesrefraction",
    "equatorialsystem",
    "focallength",
    "guideratedeclination",
    "guideraterightascension",
    "ispulseguiding",
    "rightascension",
    "rightascensionrate",
    "sideofpier",
    "siderealtime",
    "siteelevation",
    "sitelatitude",
    "sitelongitude",
    "slewing",
    "slewsettletime",
    "targetdeclination",
    "targetrightascension",
    "tracking",
    "trackingrate",
    "trackingrates",
    "utcdate",
]


def build_endpoints(
    device_number: int,
    include_axis: bool,
    include_actions: bool,
    include_park_actions: bool = False,
) -> list[Endpoint]:
    prefix = f"/api/v1/telescope/{device_number}"
    endpoints = [Endpoint("GET", f"{prefix}/{name}") for name in SAFE_GET_ENDPOINTS]
    if include_axis:
        endpoints.extend(
            [
                Endpoint("GET", f"{prefix}/canmoveaxis?Axis=0"),
                Endpoint("GET", f"{prefix}/axisrates?Axis=0"),
            ]
        )
    if include_actions:
        endpoints.extend(
            [
                Endpoint("PUT", f"{prefix}/tracking", {"Tracking": "true"}, safe=False),
                Endpoint("PUT", f"{prefix}/tracking", {"Tracking": "false"}, safe=False),
                Endpoint("PUT", f"{prefix}/abortslew", {}, safe=False),
                Endpoint("PUT", f"{prefix}/findhome", {}, safe=False),
            ]
        )
    if include_park_actions:
        endpoints.extend(
            [
                Endpoint("PUT", f"{prefix}/park", {}, safe=False),
                Endpoint("PUT", f"{prefix}/unpark", {}, safe=False),
            ]
        )
    return endpoints


def request_json(base_url: str, endpoint: Endpoint, timeout: float) -> tuple[int, dict]:
    url = base_url.rstrip("/") + endpoint.path
    data = None
    headers = {}
    if endpoint.method == "PUT":
        data = urlencode(endpoint.data or {}).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(url, data=data, method=endpoint.method, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def iter_results(base_url: str, endpoints: Iterable[Endpoint], timeout: float) -> Iterable[tuple[Endpoint, str]]:
    for endpoint in endpoints:
        try:
            status, body = request_json(base_url, endpoint, timeout)
            error_number = body.get("ErrorNumber")
            label = "OK" if status == 200 and error_number == 0 else f"ERR {error_number}"
            message = body.get("ErrorMessage", "")
            value = body.get("Value", "")
            yield endpoint, f"{label}: {value!r} {message}".strip()
        except Exception as exc:
            yield endpoint, f"HTTP/CLIENT ERROR: {exc!r}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe ASCOM Alpaca Telescope endpoints")
    parser.add_argument("--base-url", default="http://127.0.0.1:11111", help="Bridge base URL")
    parser.add_argument("--device-number", type=int, default=0, help="Telescope device number")
    parser.add_argument("--timeout", type=float, default=5.0, help="Per-request timeout in seconds")
    parser.add_argument("--include-axis", action="store_true", help="Probe AxisRates and CanMoveAxis")
    parser.add_argument("--include-actions", action="store_true", help="Also probe motion/state-changing actions")
    parser.add_argument("--include-park-actions", action="store_true", help="Also probe Park and Unpark")
    args = parser.parse_args()

    endpoints = build_endpoints(
        args.device_number,
        args.include_axis,
        args.include_actions,
        args.include_park_actions,
    )
    for endpoint, result in iter_results(args.base_url, endpoints, args.timeout):
        print(f"{endpoint.method:3} {endpoint.path:55} {result}")


if __name__ == "__main__":
    main()
