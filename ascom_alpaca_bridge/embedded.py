"""Embed the bridge in another Python application using a child process.

This module implements the external-process integration mode ("mode B"). The
host application remains independent from FastAPI and uvicorn: it opens the
ASCOM Telescope Chooser, starts ``run_bridge.py`` as a child process, waits for
the HTTP service, and connects the selected telescope through Alpaca.

Minimal one-call usage::

    from ascom_alpaca_bridge import connect_telescope_bridge

    result = connect_telescope_bridge("config.yaml")
    print(result.base_url, result.prog_id)

Use ``ExternalBridgeServer`` when the host application needs explicit control::

    from ascom_alpaca_bridge import ExternalBridgeServer

    bridge = ExternalBridgeServer("config.yaml")
    if bridge.choose_telescope():
        bridge.start()
        bridge.connect_telescope()
        print(bridge.base_url)

    # Usually called while the host application is shutting down.
    bridge.disconnect_telescope()
    bridge.stop()

``start()`` reuses a bridge already responding on the configured port. In that
case ``reused_existing`` is true and ``stop()`` leaves that external process
untouched. The convenience function returns a ``BridgeConnectionResult`` but
does not expose its controller; applications that must later stop the child
process should retain an ``ExternalBridgeServer`` instance instead.

This integration requires Windows, ASCOM Platform, pywin32, a vendor ASCOM
driver, and a usable ``config.yaml``. ``BridgeStartupError`` reports chooser or
startup failures, while ``BridgeRequestError`` reports Alpaca connection
failures. GUI applications should catch both exceptions in their button worker
and show a user-facing error without blocking the UI thread.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .chooser import choose_telescope
from .config import load_config, write_telescope_prog_id


class BridgeStartupError(RuntimeError):
    """Raised when the bridge process cannot be started or reached."""


class BridgeRequestError(RuntimeError):
    """Raised when the local Alpaca bridge returns an error response."""


@dataclass(frozen=True)
class BridgeConnectionResult:
    base_url: str
    prog_id: str
    reused_existing: bool


class ExternalBridgeServer:
    """Control an ASCOM Alpaca bridge running as a separate Python process."""

    def __init__(
        self,
        config_path: str | Path = "config.yaml",
        *,
        script_path: str | Path | None = None,
        python_executable: str | Path | None = None,
        access_log: bool = False,
        log_level: str = "info",
        opener: Callable[..., object] = urlopen,
    ) -> None:
        self.config_path = Path(config_path)
        self.script_path = Path(script_path) if script_path is not None else Path(__file__).resolve().parent.parent / "run_bridge.py"
        self.python_executable = str(python_executable or sys.executable)
        self.access_log = access_log
        self.log_level = log_level
        self._opener = opener
        self.process: subprocess.Popen[str] | None = None
        self.reused_existing = False

    @property
    def base_url(self) -> str:
        config = load_config(self.config_path)
        return f"http://127.0.0.1:{config.server.port}"

    @property
    def is_process_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def choose_telescope(self) -> str:
        config = load_config(self.config_path)
        selected_prog_id = choose_telescope(config.telescope.prog_id)
        if selected_prog_id:
            write_telescope_prog_id(self.config_path, selected_prog_id)
        return selected_prog_id

    def start(self, *, timeout: float = 15.0) -> None:
        if self.is_available(timeout=0.6):
            self.reused_existing = True
            return
        if self.is_process_running:
            self.wait_until_ready(timeout=timeout)
            return
        if not self.script_path.exists():
            raise BridgeStartupError(f"Bridge script not found: {self.script_path}")

        command = [
            self.python_executable,
            str(self.script_path),
            "--config",
            str(self.config_path),
            "--log-level",
            self.log_level,
        ]
        if self.access_log:
            command.append("--access-log")

        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                creationflags=creationflags,
            )
        except Exception as exc:
            raise BridgeStartupError(f"Unable to start bridge process: {exc}") from exc

        self.reused_existing = False
        self.wait_until_ready(timeout=timeout)

    def wait_until_ready(self, *, timeout: float = 15.0, interval: float = 0.2) -> None:
        deadline = time.monotonic() + timeout
        last_error: BaseException | None = None
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise BridgeStartupError(f"Bridge process exited with code {self.process.returncode}")
            try:
                if self.is_available(timeout=min(interval, 1.0)):
                    return
            except Exception as exc:
                last_error = exc
            time.sleep(interval)
        detail = f": {last_error}" if last_error is not None else ""
        raise BridgeStartupError(f"Bridge did not become ready within {timeout:.1f}s{detail}")

    def stop(self, *, timeout: float = 5.0) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)

    def is_available(self, *, timeout: float = 0.6) -> bool:
        try:
            with self._opener(f"{self.base_url}/status", timeout=timeout):
                return True
        except Exception:
            return False

    def connect_telescope(self, *, timeout: float = 20.0) -> None:
        self.set_telescope_connected(True, timeout=timeout)

    def disconnect_telescope(self, *, timeout: float = 20.0) -> None:
        self.set_telescope_connected(False, timeout=timeout)

    def set_telescope_connected(self, connected: bool, *, timeout: float = 20.0) -> None:
        config = load_config(self.config_path)
        payload = {
            "Connected": "true" if connected else "false",
            "ClientTransactionID": str(int(time.time() * 1000) % 1000000),
        }
        request = Request(
            f"{self.base_url}/api/v1/telescope/{config.telescope.device_number}/connected",
            data=urlencode(payload).encode("utf-8"),
            method="PUT",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with self._opener(request, timeout=timeout) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise BridgeRequestError(f"Unable to reach telescope connection endpoint: {exc}") from exc
        except Exception as exc:
            raise BridgeRequestError(f"Unable to connect telescope: {exc}") from exc

        if response_payload.get("ErrorNumber") != 0:
            message = response_payload.get("ErrorMessage") or "Alpaca error"
            raise BridgeRequestError(str(message))

    def connect_selected_telescope(self, *, timeout: float = 15.0, connect_timeout: float = 20.0) -> BridgeConnectionResult:
        selected_prog_id = self.choose_telescope()
        if not selected_prog_id:
            raise BridgeStartupError("ASCOM Telescope Chooser was cancelled")
        self.start(timeout=timeout)
        self.connect_telescope(timeout=connect_timeout)
        return BridgeConnectionResult(
            base_url=self.base_url,
            prog_id=selected_prog_id,
            reused_existing=self.reused_existing,
        )


def connect_telescope_bridge(
    config_path: str | Path = "config.yaml",
    *,
    timeout: float = 15.0,
    connect_timeout: float = 20.0,
) -> BridgeConnectionResult:
    bridge = ExternalBridgeServer(config_path)
    return bridge.connect_selected_telescope(timeout=timeout, connect_timeout=connect_timeout)
