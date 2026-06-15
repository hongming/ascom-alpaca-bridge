# ASCOM Alpaca Telescope Bridge

A lightweight Windows-only Python bridge that exposes a local ASCOM Telescope COM driver as an ASCOM Alpaca Telescope device over HTTP.

It is intended for setups where software expects an Alpaca telescope, but the mount is available only through a classic ASCOM driver.

## Features

- ASCOM Telescope Chooser integration
- ASCOM COM Telescope driver access through `pywin32`
- Alpaca Telescope HTTP API under `/api/v1/telescope/0/...`
- Alpaca management endpoints
- Alpaca UDP discovery
- Single Telescope device support
- Request logging and simple health/status endpoints
- Official Telescope member route coverage based on Alpyca Telescope documentation

## Requirements

- Windows
- ASCOM Platform
- An installed ASCOM Telescope driver
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

Choose an ASCOM Telescope driver and start the bridge:

```powershell
py run_bridge.py --config config.yaml --choose
```

Or choose once, save the selection, and start later:

```powershell
py run_bridge.py --config config.yaml --choose-only
py run_bridge.py --config config.yaml
```

The default Alpaca endpoint is:

```text
http://127.0.0.1:11111/api/v1/telescope/0
```

## Basic Checks

Health/status:

```powershell
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

- This project bridges ASCOM COM to Alpaca. It does not replace ASCOM Platform or the vendor telescope driver.
- ASCOM Chooser is a Windows desktop GUI and should be used from an interactive user session.
- If packaging as a background service later, select and save the driver first, then run the bridge with the saved config.
- See [plan.md](plan.md) for implementation notes and coverage tracking.
