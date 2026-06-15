from __future__ import annotations

import argparse
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from .ascom_driver import TelescopeDriver
from .chooser import choose_telescope
from .config import load_config, write_telescope_prog_id
from .discovery import DiscoveryServer
from .logging_middleware import install_request_logging
from .management_routes import create_management_router
from .status_routes import create_status_router
from .telescope_routes import create_telescope_router


LOG = logging.getLogger(__name__)


def create_app(config_path: str = "config.yaml") -> FastAPI:
    config = load_config(config_path)
    driver = TelescopeDriver(config.telescope.prog_id)
    discovery = DiscoveryServer(config.server.port, config.server.discovery_port)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        discovery.start()
        if config.telescope.auto_connect:
            driver.set("Connected", True)
        yield
        discovery.stop()

    app = FastAPI(title=config.server.server_name, lifespan=lifespan)
    install_request_logging(app)
    app.include_router(create_status_router(config, driver))
    app.include_router(create_management_router(config))
    app.include_router(create_telescope_router(config.telescope, driver))
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="ASCOM Telescope to Alpaca bridge")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--choose", action="store_true", help="Open ASCOM Telescope Chooser before starting")
    parser.add_argument("--choose-only", action="store_true", help="Open ASCOM Telescope Chooser, save config, and exit")
    parser.add_argument("--log-level", default="info", help="uvicorn log level")
    parser.add_argument("--access-log", action="store_true", help="Enable uvicorn access logs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config(args.config)
    if args.choose or args.choose_only:
        selected_prog_id = choose_telescope(config.telescope.prog_id)
        if not selected_prog_id:
            LOG.info("ASCOM Telescope Chooser cancelled; config unchanged")
            if args.choose_only:
                return
        else:
            write_telescope_prog_id(args.config, selected_prog_id)
            LOG.info("Saved selected Telescope ProgID to %s: %s", args.config, selected_prog_id)
            config = load_config(args.config)

        if args.choose_only:
            return

    LOG.info("Starting %s on %s:%s", config.server.server_name, config.server.host, config.server.port)

    uvicorn.run(
        create_app(args.config),
        host=config.server.host,
        port=config.server.port,
        log_level=args.log_level,
        access_log=args.access_log,
    )


if __name__ == "__main__":
    main()
