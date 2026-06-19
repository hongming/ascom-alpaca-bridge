# ASCOM Alpaca Bridge

ASCOM Alpaca 已经定义了业余天文设备 HTTP/API 化的方向。我们做的 ASCOM Alpaca Bridge，是一个轻量化桥接工具：把本机 ASCOM 设备快速发布成 Alpaca HTTP 接口，并附带简单的 Web 控制界面。

它不替代专业软件，也不重新发明协议，而是让天文圆顶、望远镜底座、相机、调焦器等设备，更容易被网络、脚本、网页和自动化系统调用。

一台电脑连接真实天文硬件后，其他十几台、上百台终端都可以通过 HTTP 获取状态数据或发送控制指令，用于展厅、科普互动、数据可视化、远程监控，或者进一步做设备矩阵控制。

目标很简单：让天文硬件从“插在一台电脑上的设备”，变成“整个网络都能调用的标准 API 节点”。

This project aims to lower the barrier for amateur astronomers to connect classic ASCOM telescope, dome, focuser, and camera drivers to modern Alpaca-compatible software.

Free and open-source. Built for amateur astronomers who want a simpler way to expose local ASCOM devices as Alpaca HTTP API nodes.

A lightweight Windows-only Python bridge that exposes local ASCOM Telescope, Dome, Focuser, and Camera COM drivers as ASCOM Alpaca devices over HTTP.

## Features

- ASCOM Telescope Chooser integration
- ASCOM Dome Chooser integration
- ASCOM Focuser Chooser integration
- ASCOM Camera Chooser integration
- ASCOM COM Telescope, Dome, Focuser, and Camera driver access through `pywin32`
- Alpaca Telescope HTTP API under `/api/v1/telescope/0/...`
- Alpaca Dome HTTP API under `/api/v1/dome/0/...`
- Alpaca Focuser HTTP API under `/api/v1/focuser/0/...`
- Alpaca Camera HTTP API under `/api/v1/camera/0/...`
- Alpaca management endpoints
- Alpaca UDP discovery
- Single Telescope, Dome, Focuser, and Camera device support
- Touch-friendly simple GUI for choosing drivers, starting/stopping the bridge, connecting devices, and opening the web dashboard
- Request logging and simple health/status endpoints
- Official Telescope, Dome, Focuser, and Camera member route coverage based on Alpyca documentation

## Requirements

- Windows
- ASCOM Platform
- An installed ASCOM Telescope driver
- An installed ASCOM Dome driver, if Dome support is enabled
- An installed ASCOM Focuser driver, if Focuser support is enabled
- An installed ASCOM Camera driver, if Camera support is enabled
- Python 3.11+

## Quick Start

Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

Create a config file:

```powershell
copy config.example.yaml config.yaml
```

The recommended way to run the bridge is the simple GUI controller:

```powershell
py run_bridge_simple_gui.py
```

The simple GUI reads `config.yaml` by default. It keeps the bridge workflow compact with a bright, professional touch-friendly device-console style: choose drivers, start/stop the bridge, connect/disconnect configured devices, and open the web dashboard. Use the web dashboard or astronomy software for detailed control.

The command-line bridge is still available for scripts, services, and advanced testing:

```powershell
py run_bridge.py --config config.yaml
```

Choose an ASCOM Telescope driver and start the bridge:

```powershell
py run_bridge.py --config config.yaml --choose
```

Choose individual drivers without starting the bridge:

```powershell
py run_bridge.py --config config.yaml --choose-only
py run_bridge.py --config config.yaml --choose-dome-only
py run_bridge.py --config config.yaml --choose-focuser-only
py run_bridge.py --config config.yaml --choose-camera-only
```

For most users, choose drivers in `run_bridge_simple_gui.py` instead of using the command-line chooser flags.

The default Alpaca endpoint is:

```text
http://127.0.0.1:11111/
http://127.0.0.1:11111/api/v1/telescope/0
http://127.0.0.1:11111/api/v1/dome/0
http://127.0.0.1:11111/api/v1/focuser/0
http://127.0.0.1:11111/api/v1/camera/0
```

## Basic Checks

Health/status:

```powershell
curl "http://127.0.0.1:11111/"
curl "http://127.0.0.1:11111/health"
curl "http://127.0.0.1:11111/status"
```

Telescope connection:

```powershell
curl "http://127.0.0.1:11111/api/v1/telescope/0/connected"
curl -X PUT -d "Connected=true&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/telescope/0/connected"
```

Read coordinates:

```powershell
curl "http://127.0.0.1:11111/api/v1/telescope/0/rightascension"
curl "http://127.0.0.1:11111/api/v1/telescope/0/declination"
```

Manual axis movement:

```powershell
curl -X PUT -d "Axis=0&Rate=1&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/telescope/0/moveaxis"
curl -X PUT -d "Axis=0&Rate=0&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/telescope/0/moveaxis"
curl -X PUT -d "Axis=1&Rate=0&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/telescope/0/moveaxis"
curl -X PUT -d "ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/telescope/0/abortslew"
```

Dome connection and status:

```powershell
curl "http://127.0.0.1:11111/api/v1/dome/0/connected"
curl -X PUT -d "Connected=true&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/dome/0/connected"
curl "http://127.0.0.1:11111/api/v1/dome/0/azimuth"
curl "http://127.0.0.1:11111/api/v1/dome/0/shutterstatus"
```

Dome controls:

```powershell
curl -X PUT -d "Azimuth=180&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/dome/0/slewtoazimuth"
curl -X PUT -d "Altitude=45&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/dome/0/slewtoaltitude"
curl -X PUT -d "ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/dome/0/openshutter"
curl -X PUT -d "ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/dome/0/closeshutter"
```

Focuser connection and status:

```powershell
curl "http://127.0.0.1:11111/api/v1/focuser/0/connected"
curl -X PUT -d "Connected=true&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/focuser/0/connected"
curl "http://127.0.0.1:11111/api/v1/focuser/0/position"
curl "http://127.0.0.1:11111/api/v1/focuser/0/temperature"
```

Focuser controls:

```powershell
curl -X PUT -d "Position=12000&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/focuser/0/move"
curl -X PUT -d "ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/focuser/0/halt"
curl -X PUT -d "TempComp=false&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/focuser/0/tempcomp"
```

Camera connection, status, and phase-two parameter setting:

```powershell
curl "http://127.0.0.1:11111/api/v1/camera/0/connected"
curl -X PUT -d "Connected=true&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/camera/0/connected"
curl "http://127.0.0.1:11111/api/v1/camera/0/camerastate"
curl "http://127.0.0.1:11111/api/v1/camera/0/imageready"
curl "http://127.0.0.1:11111/api/v1/camera/0/ccdtemperature"
curl -X PUT -d "BinX=1&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/camera/0/binx"
curl -X PUT -d "BinY=1&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/camera/0/biny"
curl -X PUT -d "Gain=100&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/camera/0/gain"
curl -X PUT -d "Offset=10&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/camera/0/offset"
curl -X PUT -d "SetCCDTemperature=-10&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/camera/0/setccdtemperature"
curl -X PUT -d "Duration=1&Light=true&ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/camera/0/startexposure"
curl "http://127.0.0.1:11111/api/v1/camera/0/imageready"
curl -X PUT -d "ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/camera/0/stopexposure"
curl -X PUT -d "ClientTransactionID=1" "http://127.0.0.1:11111/api/v1/camera/0/abortexposure"
curl "http://127.0.0.1:11111/api/v1/camera/0/imagearray"
curl "http://127.0.0.1:11111/api/v1/camera/0/imagearrayinfo"
curl "http://127.0.0.1:11111/api/v1/camera/0/imagearray.png" --output camera-test.png
curl "http://127.0.0.1:11111/api/v1/camera/0/imagearray.raw.png" --output camera-test-raw.png
curl "http://127.0.0.1:11111/api/v1/camera/0/imagearray.fits" --output camera-test.fits
```

Camera image downloads are exposed through Alpaca JSON/imagebytes. The bridge also provides `imagearray.png` as a local test helper for cropped web preview and PNG download with automatic stretch, `imagearray.raw.png` for full-frame stretched preview without crop, plus `imagearray.fits` for a lightweight FITS test download with linear pixel values. The web dashboard has an `Expose + Preview` helper that starts an exposure, polls `imageready`, refreshes status, and loads the stretched PNG preview. Start with short exposures and small ROI/binning when testing real hardware. `imagearray`, `imagearray.png`, `imagearray.raw.png`, and `imagearray.fits` are only valid after an exposure completes and `imageready` becomes `true`; `imagearrayinfo` may be `null` until the bridge has successfully downloaded an image.

## Probe Endpoints

Safe read-only probe:

```powershell
py scripts\probe_telescope_endpoints.py --base-url http://127.0.0.1:11111 --include-axis
```

Action probes may move or change the mount state. Use only in a safe simulator or hardware environment:

```powershell
py scripts\probe_telescope_endpoints.py --base-url http://127.0.0.1:11111 --include-actions
```

Park/Unpark are separate because they may block for a long time:

```powershell
py scripts\probe_telescope_endpoints.py --base-url http://127.0.0.1:11111 --include-park-actions --timeout 60
```

## Development

Install test dependencies:

```powershell
py -m pip install -r requirements-dev.txt
```

Run tests:

```powershell
py -m pytest -q
```

## Notes

- This project bridges ASCOM COM to Alpaca. It does not replace ASCOM Platform or the vendor telescope/dome/focuser/camera driver.
- ASCOM Chooser is a Windows desktop GUI and should be used from an interactive user session.
- If packaging as a background service later, select and save the driver first, then run the bridge with the saved config.
- See [plan.md](plan.md) for implementation notes and coverage tracking.
