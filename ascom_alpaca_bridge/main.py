from __future__ import annotations

import argparse
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI

from .ascom_driver import CameraDriver, DomeDriver, FocuserDriver, TelescopeDriver
from .camera_routes import create_camera_router
from .chooser import choose_camera, choose_dome, choose_focuser, choose_telescope
from .config import load_config, write_camera_prog_id, write_dome_prog_id, write_focuser_prog_id, write_telescope_prog_id
from .discovery import DiscoveryServer
from .dome_routes import create_dome_router
from .focuser_routes import create_focuser_router
from .logging_middleware import install_request_logging
from .management_routes import create_management_router
from .status_routes import create_status_router
from .telescope_routes import create_telescope_router
from .web_routes import create_web_router


LOG = logging.getLogger(__name__)


def create_app(config_path: str = "config.yaml") -> FastAPI:
    config = load_config(config_path)
    telescope_driver = TelescopeDriver(config.telescope.prog_id)
    dome_driver = DomeDriver(config.dome.prog_id) if config.dome.enabled else None
    focuser_driver = FocuserDriver(config.focuser.prog_id) if config.focuser.enabled else None
    camera_driver = CameraDriver(config.camera.prog_id) if config.camera.enabled else None
    discovery = DiscoveryServer(config.server.port, config.server.discovery_port)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        discovery.start()
        if config.telescope.auto_connect:
            telescope_driver.set("Connected", True)
        if config.dome.enabled and config.dome.auto_connect and dome_driver is not None:
            dome_driver.set("Connected", True)
        if config.focuser.enabled and config.focuser.auto_connect and focuser_driver is not None:
            focuser_driver.set("Connected", True)
        if config.camera.enabled and config.camera.auto_connect and camera_driver is not None:
            camera_driver.set("Connected", True)
        yield
        discovery.stop()

    app = FastAPI(title=config.server.server_name, lifespan=lifespan)
    install_request_logging(app)
    app.include_router(create_web_router(config))
    app.include_router(create_status_router(config, telescope_driver, dome_driver, focuser_driver, camera_driver))
    app.include_router(create_management_router(config))
    app.include_router(create_telescope_router(config.telescope, telescope_driver))
    if config.dome.enabled and dome_driver is not None:
        app.include_router(create_dome_router(config.dome, dome_driver))
    if config.focuser.enabled and focuser_driver is not None:
        app.include_router(create_focuser_router(config.focuser, focuser_driver))
    if config.camera.enabled and camera_driver is not None:
        app.include_router(create_camera_router(config.camera, camera_driver))
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="ASCOM Telescope, Dome, Focuser, and Camera to Alpaca HTTP bridge")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--choose", action="store_true", help="Open ASCOM Telescope Chooser before starting")
    parser.add_argument("--choose-only", action="store_true", help="Open ASCOM Telescope Chooser, save config, and exit")
    parser.add_argument("--choose-dome", action="store_true", help="Open ASCOM Dome Chooser before starting")
    parser.add_argument("--choose-dome-only", action="store_true", help="Open ASCOM Dome Chooser, save config, and exit")
    parser.add_argument("--choose-focuser", action="store_true", help="Open ASCOM Focuser Chooser before starting")
    parser.add_argument("--choose-focuser-only", action="store_true", help="Open ASCOM Focuser Chooser, save config, and exit")
    parser.add_argument("--choose-camera", action="store_true", help="Open ASCOM Camera Chooser before starting")
    parser.add_argument("--choose-camera-only", action="store_true", help="Open ASCOM Camera Chooser, save config, and exit")
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
    if args.choose_dome or args.choose_dome_only:
        selected_prog_id = choose_dome(config.dome.prog_id)
        if not selected_prog_id:
            LOG.info("ASCOM Dome Chooser cancelled; config unchanged")
            if args.choose_dome_only:
                return
        else:
            write_dome_prog_id(args.config, selected_prog_id)
            LOG.info("Saved selected Dome ProgID to %s: %s", args.config, selected_prog_id)
            config = load_config(args.config)

        if args.choose_dome_only:
            return
    if args.choose_focuser or args.choose_focuser_only:
        selected_prog_id = choose_focuser(config.focuser.prog_id)
        if not selected_prog_id:
            LOG.info("ASCOM Focuser Chooser cancelled; config unchanged")
            if args.choose_focuser_only:
                return
        else:
            write_focuser_prog_id(args.config, selected_prog_id)
            LOG.info("Saved selected Focuser ProgID to %s: %s", args.config, selected_prog_id)
            config = load_config(args.config)

        if args.choose_focuser_only:
            return
    if args.choose_camera or args.choose_camera_only:
        selected_prog_id = choose_camera(config.camera.prog_id)
        if not selected_prog_id:
            LOG.info("ASCOM Camera Chooser cancelled; config unchanged")
            if args.choose_camera_only:
                return
        else:
            write_camera_prog_id(args.config, selected_prog_id)
            LOG.info("Saved selected Camera ProgID to %s: %s", args.config, selected_prog_id)
            config = load_config(args.config)

        if args.choose_camera_only:
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
