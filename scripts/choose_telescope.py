from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ascom_alpaca_bridge.chooser import choose_telescope
from ascom_alpaca_bridge.config import load_config, write_telescope_prog_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Open ASCOM Telescope Chooser and save the selected ProgID")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--no-save", action="store_true", help="Print the selected ProgID without writing config")
    args = parser.parse_args()

    config = load_config(args.config)
    selected = choose_telescope(config.telescope.prog_id)
    if not selected:
        print("Chooser cancelled; config unchanged.")
        return

    print(f"Selected Telescope ProgID: {selected}")
    if not args.no_save:
        write_telescope_prog_id(args.config, selected)
        print(f"Saved to {args.config}")


if __name__ == "__main__":
    main()
