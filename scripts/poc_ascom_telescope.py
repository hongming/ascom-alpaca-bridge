from __future__ import annotations

import argparse
import platform


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify direct ASCOM Telescope COM access")
    parser.add_argument("--prog-id", default="ASCOM.Simulator.Telescope", help="ASCOM Telescope ProgID")
    parser.add_argument("--connect", action="store_true", help="Set Connected=true before reading values")
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
        telescope.Connected = True

    print(f"ProgID: {args.prog_id}")
    print(f"Name: {telescope.Name}")
    print(f"Description: {telescope.Description}")
    print(f"DriverInfo: {telescope.DriverInfo}")
    print(f"DriverVersion: {telescope.DriverVersion}")
    print(f"InterfaceVersion: {telescope.InterfaceVersion}")
    print(f"Connected: {telescope.Connected}")

    if telescope.Connected:
        print(f"RightAscension: {telescope.RightAscension}")
        print(f"Declination: {telescope.Declination}")
        print(f"Altitude: {telescope.Altitude}")
        print(f"Azimuth: {telescope.Azimuth}")
        print(f"Tracking: {telescope.Tracking}")
        print(f"Slewing: {telescope.Slewing}")


if __name__ == "__main__":
    main()
