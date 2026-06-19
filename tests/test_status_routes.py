from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ascom_alpaca_bridge.ascom_driver import DriverBusyError
from ascom_alpaca_bridge.config import AppConfig, CameraConfig, DomeConfig, FocuserConfig, ServerConfig, TelescopeConfig
from ascom_alpaca_bridge.status_routes import create_status_router


class FakeStatusDriver:
    def __init__(self, connected: bool = True, busy: bool = False) -> None:
        self.connected = connected
        self.busy = busy

    def connected_nowait(self) -> bool:
        if self.busy:
            raise DriverBusyError()
        return self.connected


def test_status_keeps_other_devices_available_when_telescope_is_busy() -> None:
    config = AppConfig(
        server=ServerConfig(),
        telescope=TelescopeConfig(),
        dome=DomeConfig(enabled=True),
        focuser=FocuserConfig(enabled=True),
        camera=CameraConfig(enabled=True),
    )
    app = FastAPI()
    app.include_router(
        create_status_router(
            config,
            FakeStatusDriver(busy=True),  # type: ignore[arg-type]
            FakeStatusDriver(),  # type: ignore[arg-type]
            FakeStatusDriver(),  # type: ignore[arg-type]
            FakeStatusDriver(),  # type: ignore[arg-type]
        )
    )
    client = TestClient(app)

    payload = client.get("/status").json()

    assert payload["ok"] is True
    assert payload["telescope"]["connected"] is None
    assert payload["telescope"]["busy"] is True
    assert payload["telescope"]["error_number"] == 0x408
    assert payload["dome"]["connected"] is True
    assert payload["focuser"]["connected"] is True
    assert payload["camera"]["connected"] is True
