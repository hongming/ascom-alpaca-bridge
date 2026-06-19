from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ascom_alpaca_bridge.config import DomeConfig
from ascom_alpaca_bridge.dome_routes import create_dome_router


class FakeDomeDriver:
    def __init__(self) -> None:
        self.values = {
            "Connected": True,
            "Connecting": False,
            "DeviceState": [],
            "Altitude": 45.0,
            "AtHome": False,
            "AtPark": False,
            "Azimuth": 180.0,
            "CanFindHome": True,
            "CanPark": True,
            "CanSetAltitude": True,
            "CanSetAzimuth": True,
            "CanSetPark": True,
            "CanSetShutter": True,
            "CanSlave": True,
            "CanSyncAzimuth": True,
            "ShutterStatus": 1,
            "Slaved": False,
            "Slewing": False,
        }
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def get(self, name: str) -> object:
        return self.values[name]

    def set(self, name: str, value: object) -> None:
        self.values[name] = value

    def invoke(self, name: str, *args: object) -> object:
        self.calls.append((name, args))
        if name in {"SlewToAzimuth", "SlewToAltitude", "Park", "FindHome"}:
            self.values["Slewing"] = True
        return None


def make_client() -> tuple[TestClient, FakeDomeDriver]:
    driver = FakeDomeDriver()
    app = FastAPI()
    app.include_router(create_dome_router(DomeConfig(), driver))
    return TestClient(app), driver


def test_dome_status_properties() -> None:
    client, _driver = make_client()

    assert client.get("/api/v1/dome/0/azimuth").json()["Value"] == 180.0
    assert client.get("/api/v1/dome/0/altitude").json()["Value"] == 45.0
    assert client.get("/api/v1/dome/0/shutterstatus").json()["Value"] == 1
    assert client.get("/api/v1/dome/0/cansetshutter").json()["Value"] is True


def test_dome_connected_and_slaved_put() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/dome/0/connected", data={"Connected": "false"}).json()["ErrorNumber"] == 0
    assert driver.values["Connected"] is False

    driver.values["Connected"] = True
    assert client.put("/api/v1/dome/0/slaved", data={"Slaved": "true"}).json()["ErrorNumber"] == 0
    assert driver.values["Slaved"] is True


def test_dome_shutter_and_motion_actions() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/dome/0/openshutter").json()["ErrorNumber"] == 0
    assert client.put("/api/v1/dome/0/closeshutter").json()["ErrorNumber"] == 0
    assert client.put("/api/v1/dome/0/slewtoazimuth", data={"Azimuth": "123.4"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/dome/0/slewtoaltitude", data={"Altitude": "67.8"}).json()["ErrorNumber"] == 0
    assert client.put("/api/v1/dome/0/synctoazimuth", data={"Azimuth": "120"}).json()["ErrorNumber"] == 0
    assert ("OpenShutter", ()) in driver.calls
    assert ("CloseShutter", ()) in driver.calls
    assert ("SlewToAzimuth", (123.4,)) in driver.calls
    assert ("SlewToAltitude", (67.8,)) in driver.calls
    assert ("SyncToAzimuth", (120.0,)) in driver.calls


def test_dome_connect_disconnect_shortcuts() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/dome/0/disconnect").json()["ErrorNumber"] == 0
    assert driver.values["Connected"] is False
    assert client.put("/api/v1/dome/0/connect").json()["ErrorNumber"] == 0
    assert driver.values["Connected"] is True

