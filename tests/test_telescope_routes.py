from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ascom_alpaca_bridge.config import TelescopeConfig
from ascom_alpaca_bridge.telescope_routes import create_telescope_router


class FakeTelescopeDriver:
    def __init__(self) -> None:
        self.values = {
            "Connected": True,
            "Connecting": False,
            "DeviceState": [],
            "AlignmentMode": 0,
            "ApertureArea": 0.0,
            "ApertureDiameter": 0.0,
            "FocalLength": 0.0,
            "IsPulseGuiding": False,
            "SlewSettleTime": 0,
            "Tracking": False,
            "Slewing": False,
            "CanFindHome": True,
            "CanPark": True,
            "CanUnpark": True,
        }
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def get(self, name: str) -> object:
        return self.values[name]

    def set(self, name: str, value: object) -> None:
        self.values[name] = value

    def invoke(self, name: str, *args: object) -> object:
        self.calls.append((name, args))
        if name == "SlewToCoordinatesAsync":
            self.values["Slewing"] = True
        if name in {"Park", "Unpark", "FindHome", "SlewToTarget", "SlewToTargetAsync", "SyncToTarget"}:
            return None
        return None


def make_client() -> tuple[TestClient, FakeTelescopeDriver]:
    driver = FakeTelescopeDriver()
    app = FastAPI()
    app.include_router(create_telescope_router(TelescopeConfig(), driver))
    return TestClient(app), driver


def test_tracking_get_and_put() -> None:
    client, driver = make_client()

    assert client.get("/api/v1/telescope/0/tracking").json()["Value"] is False

    response = client.put("/api/v1/telescope/0/tracking", data={"Tracking": "true"})

    assert response.json()["ErrorNumber"] == 0
    assert driver.values["Tracking"] is True


def test_slewing_get() -> None:
    client, _driver = make_client()

    response = client.get("/api/v1/telescope/0/slewing")

    assert response.json()["Value"] is False


def test_park_unpark_and_findhome() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/telescope/0/park").json()["ErrorNumber"] == 0
    assert client.put("/api/v1/telescope/0/unpark").json()["ErrorNumber"] == 0
    assert client.put("/api/v1/telescope/0/findhome").json()["ErrorNumber"] == 0
    assert ("Park", ()) in driver.calls
    assert ("Unpark", ()) in driver.calls
    assert ("FindHome", ()) in driver.calls


def test_slew_to_coordinates_async() -> None:
    client, driver = make_client()

    response = client.put(
        "/api/v1/telescope/0/slewtocoordinatesasync",
        data={"RightAscension": "12.5", "Declination": "-30.25"},
    )

    assert response.json()["ErrorNumber"] == 0
    assert ("SlewToCoordinatesAsync", (12.5, -30.25)) in driver.calls
    assert client.get("/api/v1/telescope/0/slewing").json()["Value"] is True


def test_remaining_official_members_added_from_local_mhtml() -> None:
    client, driver = make_client()

    for member in [
        "alignmentmode",
        "aperturearea",
        "aperturediameter",
        "connecting",
        "devicestate",
        "focallength",
        "ispulseguiding",
        "slewsettletime",
    ]:
        response = client.get(f"/api/v1/telescope/0/{member}")
        assert response.json()["ErrorNumber"] == 0, member

    assert client.put("/api/v1/telescope/0/connect").json()["ErrorNumber"] == 0
    assert driver.values["Connected"] is True
    assert client.put("/api/v1/telescope/0/disconnect").json()["ErrorNumber"] == 0
    assert driver.values["Connected"] is False

    driver.values["Connected"] = True
    assert client.put("/api/v1/telescope/0/slewsettletime", data={"SlewSettleTime": "2"}).json()["ErrorNumber"] == 0
    assert driver.values["SlewSettleTime"] == 2
    assert client.put("/api/v1/telescope/0/slewtotarget").json()["ErrorNumber"] == 0
    assert client.put("/api/v1/telescope/0/slewtotargetasync").json()["ErrorNumber"] == 0
    assert client.put("/api/v1/telescope/0/synctotarget").json()["ErrorNumber"] == 0
    assert ("SlewToTarget", ()) in driver.calls
    assert ("SlewToTargetAsync", ()) in driver.calls
    assert ("SyncToTarget", ()) in driver.calls
