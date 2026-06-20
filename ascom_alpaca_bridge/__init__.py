"""Lightweight ASCOM Telescope to Alpaca bridge."""

__version__ = "0.1.0"

from .embedded import (
    BridgeConnectionResult,
    BridgeRequestError,
    BridgeStartupError,
    ExternalBridgeServer,
    connect_telescope_bridge,
)

__all__ = [
    "BridgeConnectionResult",
    "BridgeRequestError",
    "BridgeStartupError",
    "ExternalBridgeServer",
    "connect_telescope_bridge",
]
