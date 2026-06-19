from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ascom_alpaca_bridge.config import AppConfig, CameraConfig, DomeConfig, FocuserConfig, ServerConfig, TelescopeConfig
from ascom_alpaca_bridge.web_routes import create_web_router


def test_web_dashboard_contains_device_paths() -> None:
    config = AppConfig(
        server=ServerConfig(port=11111),
        telescope=TelescopeConfig(),
        dome=DomeConfig(enabled=True),
        focuser=FocuserConfig(enabled=True),
        camera=CameraConfig(enabled=True),
    )
    app = FastAPI()
    app.include_router(create_web_router(config))
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>ASCOM Alpaca Bridge</title>" in response.text
    assert "/management/v1/configureddevices" in response.text
    assert "/api/v1/${device.DeviceType.toLowerCase()}/${device.DeviceNumber}" in response.text
    assert "Move rate" in response.text
    assert "https://ascom-standards.org/alpyca/alpaca.telescope.html" in response.text
    assert "https://ascom-standards.org/alpyca/alpaca.dome.html#alpaca.dome.Dome" in response.text
    assert "https://ascom-standards.org/alpyca/alpaca.focuser.html#alpaca.focuser.Focuser" in response.text
    assert "https://ascom-standards.org/alpyca/alpaca.camera.html#alpaca.camera.Camera" in response.text
    assert "Link to Alpaca Telescope API document" in response.text
    assert 'target="_blank" rel="noopener noreferrer"' in response.text
    assert "telescopeRateOptions" in response.text
    assert "/axisrates?Axis=0" in response.text
    assert "/axisrates?Axis=1" in response.text
    assert 'data-long-put="${path}/park"' in response.text
    assert 'data-long-put="${path}/unpark"' in response.text
    assert 'data-long-put="${path}/findhome"' in response.text
    assert "Tracking Yes" in response.text
    assert "Tracking No" in response.text
    assert "data-rate-store" in response.text
    assert 'data-move-axis="${path}"' in response.text
    assert 'data-stop-axis="${path}"' in response.text
    assert "↑" in response.text
    assert "←" in response.text
    assert "→" in response.text
    assert "↓" in response.text
    assert "Telescope stop command sent" in response.text
    assert "TempComp On" in response.text
    assert "Open" in response.text
    assert "Stop Exposure" in response.text
    assert 'Camera: ["connected", "camerastate", "imageready", "ccdtemperature", "cooleron", "coolerpower", "percentcompleted", "cameraxsize", "cameraysize", "startx", "starty", "numx", "numy", "binx", "biny"]' in response.text
    assert "inputPlaceholder" in response.text
    assert 'placeholder="${inputPlaceholder(values, "numx", "Camera X")}"' in response.text
    assert 'placeholder="${inputPlaceholder(values, "numy", "Camera Y")}"' in response.text
    assert 'id="cameraStartX"' in response.text
    assert 'id="cameraStartY"' in response.text
    assert 'id="cameraDuration" type="number" step="0.1" inputmode="decimal" value="1"' in response.text
    assert "Expose + Preview" in response.text
    assert "Preview PNG" in response.text
    assert "Raw Preview" in response.text
    assert "Download PNG" in response.text
    assert "Download Raw PNG" in response.text
    assert "Download FITS" in response.text
    assert "imagearray.fits" in response.text
    assert "imagearray.raw.png" in response.text
    assert "isUnsupportedPayload" in response.text
    assert "isBusyValue" in response.text
    assert 'values.connected === false || isBusyValue(values.connected)' in response.text
    assert '<span class="muted">Unsupported</span>' in response.text
    assert "waitForCameraImageReady" in response.text
    assert "refreshDeviceByPath" in response.text
    assert "deviceInfoFromPath" in response.text
    assert "URL.createObjectURL(blob)" in response.text
    assert "target.dataset.objectUrl" in response.text
    assert "await refreshDeviceByPath(path);\n          await loadCameraPreview" not in response.text
    assert "configuredDevicesCache" in response.text
    assert 'configuredDevicesCache = devices;' in response.text
    refresh_device_body = response.text.split("async function refreshDeviceByPath", 1)[1].split("function sleep", 1)[0]
    assert 'getJson("/management/v1/configureddevices")' not in refresh_device_body
    assert '<span class="muted">Unavailable</span>' in response.text
    assert "Raw Preview keeps the full frame" in response.text
