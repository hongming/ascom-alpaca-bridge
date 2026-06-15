from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI, Request


LOG = logging.getLogger("ascom_alpaca_bridge.http")


def install_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_request(request: Request, call_next: Any) -> Any:
        started = time.perf_counter()
        response = await call_next(request)
        if request.url.path in {"/health", "/status"}:
            return response
        elapsed_ms = (time.perf_counter() - started) * 1000
        LOG.info(
            "%s %s -> %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
