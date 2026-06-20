from __future__ import annotations

from pathlib import Path
from urllib.request import Request

from ascom_alpaca_bridge.embedded import ExternalBridgeServer


class FakeResponse:
    def __init__(self, payload: bytes = b'{"ErrorNumber": 0}') -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def write_config(path: Path, port: int = 22222) -> None:
    path.write_text(
        f"""
server:
  port: {port}
telescope:
  device_number: 3
  prog_id: ASCOM.Test.Telescope
""".strip(),
        encoding="utf-8",
    )


def test_base_url_uses_config_port(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_config(config_path, port=23456)

    bridge = ExternalBridgeServer(config_path)

    assert bridge.base_url == "http://127.0.0.1:23456"


def test_connect_telescope_puts_alpaca_connected_payload(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_config(config_path)
    calls: list[tuple[object, float | None]] = []

    def opener(target: object, timeout: float | None = None) -> FakeResponse:
        calls.append((target, timeout))
        return FakeResponse()

    bridge = ExternalBridgeServer(config_path, opener=opener)

    bridge.connect_telescope(timeout=9)

    request, timeout = calls[0]
    assert isinstance(request, Request)
    assert request.full_url == "http://127.0.0.1:22222/api/v1/telescope/3/connected"
    assert request.get_method() == "PUT"
    assert request.headers["Content-type"] == "application/x-www-form-urlencoded"
    assert b"Connected=true" in request.data
    assert timeout == 9


def test_start_reuses_existing_bridge_without_spawning(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_config(config_path)

    def opener(target: object, timeout: float | None = None) -> FakeResponse:
        return FakeResponse()

    bridge = ExternalBridgeServer(config_path, opener=opener)

    bridge.start()

    assert bridge.reused_existing is True
    assert bridge.process is None


def test_start_spawns_bridge_when_status_is_unavailable(monkeypatch: object, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    script_path = tmp_path / "run_bridge.py"
    write_config(config_path)
    script_path.write_text("print('bridge')", encoding="utf-8")
    opened = 0
    commands: list[list[str]] = []

    class FakeProcess:
        returncode = None

        def poll(self) -> int | None:
            return None

    def opener(target: object, timeout: float | None = None) -> FakeResponse:
        nonlocal opened
        opened += 1
        if opened == 1:
            raise OSError("not ready")
        return FakeResponse()

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        commands.append(command)
        return FakeProcess()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    bridge = ExternalBridgeServer(
        config_path,
        script_path=script_path,
        python_executable="python-test",
        access_log=True,
        opener=opener,
    )

    bridge.start(timeout=1)

    assert commands == [
        [
            "python-test",
            str(script_path),
            "--config",
            str(config_path),
            "--log-level",
            "info",
            "--access-log",
        ]
    ]
    assert bridge.reused_existing is False
