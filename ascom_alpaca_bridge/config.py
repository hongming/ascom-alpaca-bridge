from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 11111
    discovery_port: int = 32227
    server_name: str = "Python ASCOM Telescope Bridge"
    manufacturer: str = "Local Python Bridge"
    manufacturer_version: str = "0.1.0"
    location: str = "Local Windows host"


@dataclass(frozen=True)
class TelescopeConfig:
    device_number: int = 0
    prog_id: str = "ASCOM.Simulator.Telescope"
    display_name: str = "ASCOM Telescope"
    unique_id: str = "python-ascom-telescope-0"
    auto_connect: bool = False


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    telescope: TelescopeConfig


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{name}' must be a mapping")
    return value


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        example_path = Path("config.example.yaml")
        config_path = example_path if example_path.exists() else config_path

    raw: dict[str, Any] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if loaded is not None:
            if not isinstance(loaded, dict):
                raise ValueError("Config file root must be a mapping")
            raw = loaded

    return AppConfig(
        server=ServerConfig(**_section(raw, "server")),
        telescope=TelescopeConfig(**_section(raw, "telescope")),
    )


def write_telescope_prog_id(path: str | Path, prog_id: str) -> None:
    config_path = Path(path)
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if loaded is None:
            raw: dict[str, Any] = {}
        elif isinstance(loaded, dict):
            raw = loaded
        else:
            raise ValueError("Config file root must be a mapping")
    else:
        example_path = Path("config.example.yaml")
        if example_path.exists():
            loaded = yaml.safe_load(example_path.read_text(encoding="utf-8"))
            raw = loaded if isinstance(loaded, dict) else {}
        else:
            raw = {}

    telescope = raw.setdefault("telescope", {})
    if not isinstance(telescope, dict):
        raise ValueError("Config section 'telescope' must be a mapping")
    telescope["prog_id"] = prog_id

    config_path.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
