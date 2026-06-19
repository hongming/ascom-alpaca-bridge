from __future__ import annotations

import time
from threading import Event, Thread

import pytest

from ascom_alpaca_bridge.ascom_driver import AscomDriver, AscomDriverError, DriverBusyError


class WriteOnlyConnectedDriver:
    def __init__(self) -> None:
        self._connected = False

    @property
    def Connected(self) -> bool:
        raise RuntimeError("Property Unknown is not implemented in this driver.")

    @Connected.setter
    def Connected(self, value: bool) -> None:
        self._connected = value


class FailingConnectedDriver:
    @property
    def Connected(self) -> bool:
        raise RuntimeError("Property Unknown is not implemented in this driver.")


class RpcUnavailableDriver:
    @property
    def Connected(self) -> bool:
        raise RuntimeError("RPC 服务器不可用。 (异常来自 HRESULT:0x800706BA)")


def test_connected_get_uses_cache_after_successful_set_when_driver_get_is_not_implemented() -> None:
    driver = AscomDriver("ASCOM.Test.Camera")
    driver._driver = WriteOnlyConnectedDriver()

    driver.set("Connected", True)

    assert driver.get("Connected") is True


def test_connected_get_without_cache_still_reports_driver_error() -> None:
    driver = AscomDriver("ASCOM.Test.Camera")
    driver._driver = FailingConnectedDriver()

    with pytest.raises(AscomDriverError):
        driver.get("Connected")


def test_rpc_unavailable_is_reported_as_not_connected() -> None:
    driver = AscomDriver("ASCOM.Test.Dome")
    driver._driver = RpcUnavailableDriver()

    with pytest.raises(AscomDriverError) as exc_info:
        driver.get("Connected")

    assert exc_info.value.error_number == 0x407


def test_connected_nowait_does_not_load_uninitialized_driver() -> None:
    driver = AscomDriver("ASCOM.Test.Camera")

    assert driver.connected_nowait() is False
    assert driver.is_loaded is False


def test_get_nowait_reports_busy_when_driver_lock_is_held() -> None:
    driver = AscomDriver("ASCOM.Test.Camera")
    driver._driver = WriteOnlyConnectedDriver()
    lock_held = Event()

    def hold_lock() -> None:
        def wait(_driver: object) -> None:
            lock_held.set()
            time.sleep(0.2)

        driver.call(wait)

    thread = Thread(target=hold_lock)
    thread.start()
    assert lock_held.wait(timeout=1)

    with pytest.raises(DriverBusyError):
        driver.get_nowait("Connected")

    thread.join()
