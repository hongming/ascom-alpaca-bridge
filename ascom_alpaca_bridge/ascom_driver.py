from __future__ import annotations

import platform
from threading import RLock
from typing import Any, Callable, TypeVar


T = TypeVar("T")


class AscomDriverError(RuntimeError):
    def __init__(self, message: str, error_number: int = 0x500) -> None:
        super().__init__(message)
        self.error_number = error_number


class UnsupportedActionError(AscomDriverError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_number=0x401)


def _error_number_from_exception(exc: Exception) -> int:
    message = str(exc).lower()
    if "not connected" in message or "未连接" in message:
        return 0x407
    if "not implemented" in message or "not supported" in message or "不支持" in message or "未实现" in message:
        return 0x400
    if "invalid value" in message or "invalid parameter" in message or "参数" in message:
        return 0x401
    return 0x500


class TelescopeDriver:
    def __init__(self, prog_id: str) -> None:
        self.prog_id = prog_id
        self._lock = RLock()
        self._driver: Any | None = None

    def connect_com(self) -> None:
        if platform.system() != "Windows":
            raise AscomDriverError("ASCOM COM drivers are only available on Windows")

        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise AscomDriverError("pywin32 is required to use ASCOM COM drivers") from exc

        with self._lock:
            pythoncom.CoInitialize()
            try:
                self._driver = win32com.client.Dispatch(self.prog_id)
            except Exception as exc:
                raise AscomDriverError(f"Unable to create ASCOM driver '{self.prog_id}': {exc}") from exc

    @property
    def driver(self) -> Any:
        if self._driver is None:
            self.connect_com()
        return self._driver

    def call(self, callback: Callable[[Any], T]) -> T:
        with self._lock:
            try:
                return callback(self.driver)
            except AscomDriverError:
                raise
            except Exception as exc:
                raise AscomDriverError(str(exc), error_number=_error_number_from_exception(exc)) from exc

    def get(self, property_name: str) -> Any:
        return self.call(lambda driver: getattr(driver, property_name))

    def set(self, property_name: str, value: Any) -> None:
        def setter(driver: Any) -> None:
            setattr(driver, property_name, value)

        self.call(setter)

    def invoke(self, method_name: str, *args: Any) -> Any:
        def invoker(driver: Any) -> Any:
            method = getattr(driver, method_name)
            return method(*args)

        return self.call(invoker)
