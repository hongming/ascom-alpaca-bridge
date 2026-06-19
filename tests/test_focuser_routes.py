from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ascom_alpaca_bridge.config import FocuserConfig
from ascom_alpaca_bridge.focuser_routes import create_focuser_router


class FakeFocuserDriver:
    def __init__(self) -> None:
        self.values = {
            "Connected": True,
            "Connecting": False,
            "DeviceState": [],
            "Absolute": True,
            "IsMoving": False,
            "MaxIncrement": 1000,
            "MaxStep": 60000,
            "Position": 12000,
            "StepSize": 1.0,
            "TempComp": False,
            "TempCompAvailable": True,
            "Temperature": 12.5,
        }
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def get(self, name: str) -> object:
        return self.values[name]

    def set(self, name: str, value: object) -> None:
        self.values[name] = value

    def invoke(self, name: str, *args: object) -> object:
        self.calls.append((name, args))
        if name == "Move":
            self.values["Position"] = args[0]
            self.values["IsMoving"] = True
        if name == "Halt":
            self.values["IsMoving"] = False
        return None


def make_client() -> tuple[TestClient, FakeFocuserDriver]:
    driver = FakeFocuserDriver()
    app = FastAPI()
    app.include_router(create_focuser_router(FocuserConfig(), driver))
    return TestClient(app), driver


def test_focuser_status_properties() -> None:
    client, _driver = make_client()

    assert client.get("/api/v1/focuser/0/absolute").json()["Value"] is True
    assert client.get("/api/v1/focuser/0/position").json()["Value"] == 12000
    assert client.get("/api/v1/focuser/0/maxstep").json()["Value"] == 60000
    assert client.get("/api/v1/focuser/0/temperature").json()["Value"] == 12.5


def test_focuser_connected_and_tempcomp_put() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/focuser/0/connected", data={"Connected": "false"}).json()["ErrorNumber"] == 0
    assert driver.values["Connected"] is False

    driver.values["Connected"] = True
    assert client.put("/api/v1/focuser/0/tempcomp", data={"TempComp": "true"}).json()["ErrorNumber"] == 0
    assert driver.values["TempComp"] is True


def test_focuser_move_and_halt() -> None:
    client, driver = make_client()

    assert client.put("/api/v1/focuser/0/move", data={"Position": "13579"}).json()["ErrorNumber"] == 0
    assert ("Move", (13579,)) in driver.calls
    assert client.get("/api/v1/focuser/0/ismoving").json()["Value"] is True

    assert client.put("/api/v1/focuser/0/halt").json()["ErrorNumber"] == 0
    assert ("Halt", ()) in driver.calls
    assert client.get("/api/v1/focuser/0/ismoving").json()["Value"] is False
