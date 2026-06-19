from __future__ import annotations

import platform
import queue
from dataclasses import dataclass
from threading import Event, RLock, Thread
from typing import Any, Callable, TypeVar


T = TypeVar("T")


@dataclass
class _DriverTask:
    callback: Callable[[Any], Any]
    done: Event
    result: Any = None
    error: BaseException | None = None


class AscomDriverError(RuntimeError):
    def __init__(self, message: str, error_number: int = 0x500) -> None:
        super().__init__(message)
        self.error_number = error_number


class UnsupportedActionError(AscomDriverError):
    def __init__(self, message: str) -> None:
        super().__init__(message, error_number=0x401)


class DriverBusyError(AscomDriverError):
    def __init__(self, message: str = "ASCOM driver is busy") -> None:
        super().__init__(message, error_number=0x408)


def _error_number_from_exception(exc: Exception) -> int:
    message = str(exc).lower()
    if "not connected" in message or "未连接" in message:
        return 0x407
    if (
        "rpc server unavailable" in message
        or "rpc 服务器不可用" in message
        or "0x800706ba" in message
        or "-2147023174" in message
    ):
        return 0x407
    if (
        "no image available" in message
        or "no image data" in message
        or "invalid operation" in message
        or "parameter name: source" in message
        or "参数名: source" in message
    ):
        return 0x40B
    if "not implemented" in message or "not supported" in message or "不支持" in message or "未实现" in message:
        return 0x400
    if "invalid value" in message or "invalid parameter" in message or "参数" in message:
        return 0x401
    return 0x500


class AscomDriver:
    def __init__(self, prog_id: str) -> None:
        self.prog_id = prog_id
        self._lock = RLock()
        self._driver: Any | None = None
        self._property_cache: dict[str, Any] = {}
        self._task_queue: queue.Queue[_DriverTask] = queue.Queue()
        self._worker: Thread | None = None
        self._worker_lock = RLock()

    def connect_com(self) -> None:
        self.call(lambda _driver: None)

    @property
    def is_loaded(self) -> bool:
        return self._driver is not None

    @property
    def driver(self) -> Any:
        raise AscomDriverError("Direct driver access is not available; use call/get/set/invoke")

    def _ensure_worker(self) -> None:
        with self._worker_lock:
            if self._worker is not None and self._worker.is_alive():
                return
            self._worker = Thread(target=self._worker_loop, name=f"ASCOM {self.prog_id}", daemon=True)
            self._worker.start()

    def _ensure_driver_on_worker(self) -> Any:
        if self._driver is not None:
            return self._driver
        if platform.system() != "Windows":
            raise AscomDriverError("ASCOM COM drivers are only available on Windows")
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise AscomDriverError("pywin32 is required to use ASCOM COM drivers") from exc
        pythoncom.CoInitialize()
        try:
            self._driver = win32com.client.Dispatch(self.prog_id)
        except Exception as exc:
            raise AscomDriverError(f"Unable to create ASCOM driver '{self.prog_id}': {exc}") from exc
        return self._driver

    def _worker_loop(self) -> None:
        while True:
            task = self._task_queue.get()
            try:
                driver = self._ensure_driver_on_worker()
                task.result = task.callback(driver)
            except AscomDriverError as exc:
                task.error = exc
            except Exception as exc:
                task.error = AscomDriverError(str(exc), error_number=_error_number_from_exception(exc))
            finally:
                task.done.set()

    def _run_on_worker(self, callback: Callable[[Any], T]) -> T:
        self._ensure_worker()
        task = _DriverTask(callback=callback, done=Event())
        self._task_queue.put(task)
        task.done.wait()
        if task.error is not None:
            raise task.error
        return task.result

    def call(self, callback: Callable[[Any], T]) -> T:
        with self._lock:
            return self._run_on_worker(callback)

    def call_nowait(self, callback: Callable[[Any], T]) -> T:
        if not self._lock.acquire(blocking=False):
            raise DriverBusyError()
        try:
            return self._run_on_worker(callback)
        finally:
            self._lock.release()

    def get(self, property_name: str) -> Any:
        try:
            return self.call(lambda driver: getattr(driver, property_name))
        except AscomDriverError as exc:
            if property_name == "Connected" and property_name in self._property_cache and exc.error_number == 0x400:
                return self._property_cache[property_name]
            raise

    def get_nowait(self, property_name: str) -> Any:
        try:
            return self.call_nowait(lambda driver: getattr(driver, property_name))
        except AscomDriverError as exc:
            if property_name == "Connected" and property_name in self._property_cache and exc.error_number == 0x400:
                return self._property_cache[property_name]
            raise

    def connected_nowait(self) -> bool:
        if not self.is_loaded:
            return bool(self._property_cache.get("Connected", False))
        return bool(self.get_nowait("Connected"))

    def set(self, property_name: str, value: Any) -> None:
        def setter(driver: Any) -> None:
            setattr(driver, property_name, value)

        self.call(setter)
        if property_name == "Connected":
            self._property_cache[property_name] = value

    def invoke(self, method_name: str, *args: Any) -> Any:
        def invoker(driver: Any) -> Any:
            method = getattr(driver, method_name)
            return method(*args)

        return self.call(invoker)


TelescopeDriver = AscomDriver
DomeDriver = AscomDriver
FocuserDriver = AscomDriver
CameraDriver = AscomDriver
