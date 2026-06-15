from __future__ import annotations

import argparse
import platform


PROPERTIES = [
    "Connected",
    "Name",
    "Description",
    "DriverInfo",
    "DriverVersion",
    "InterfaceVersion",
    "RightAscension",
    "Declination",
    "Altitude",
    "Azimuth",
    "SiderealTime",
    "SiteLatitude",
    "SiteLongitude",
    "SiteElevation",
    "Tracking",
    "Slewing",
    "AtPark",
    "AtHome",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Read ASCOM Telescope properties one by one")
    parser.add_argument("--prog-id", required=True, help="ASCOM Telescope ProgID")
    parser.add_argument("--connect", action="store_true", help="Set Connected=true before reading properties")
    args = parser.parse_args()

    if platform.system() != "Windows":
        raise SystemExit("ASCOM COM access is only available on Windows")

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise SystemExit("pywin32 is required. Run: py -m pip install pywin32") from exc

    pythoncom.CoInitialize()
    telescope = win32com.client.Dispatch(args.prog_id)

    if args.connect:
        print("Setting Connected=true")
        telescope.Connected = True

    for property_name in PROPERTIES:
        try:
            print(f"{property_name}: OK: {getattr(telescope, property_name)!r}")
        except Exception as exc:
            print(f"{property_name}: ERROR: {exc!r}")


if __name__ == "__main__":
    main()
