from __future__ import annotations

import json
import logging
import socket
import threading


LOG = logging.getLogger(__name__)


class DiscoveryServer:
    def __init__(self, http_port: int, discovery_port: int = 32227) -> None:
        self.http_port = http_port
        self.discovery_port = discovery_port
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket: socket.socket | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._serve, name="alpaca-discovery", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._socket is not None:
            self._socket.close()

    def _serve(self) -> None:
        response = json.dumps({"AlpacaPort": self.http_port}).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket = sock
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self.discovery_port))
        LOG.info("Alpaca discovery listening on UDP %s", self.discovery_port)

        while not self._stop.is_set():
            try:
                data, address = sock.recvfrom(1024)
            except OSError:
                break

            if data.strip() == b"alpacadiscovery1":
                try:
                    sock.sendto(response, address)
                except OSError as exc:
                    LOG.warning("Failed to send Alpaca discovery response: %s", exc)
