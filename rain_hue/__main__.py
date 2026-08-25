"""CLI entrypoint: python -m rain_hue <command>.

Designed for cron/systemd: one command = one run, then exit.
"""

import argparse
import logging
import sys

from .config import load
from .core import run_once

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(prog="rain_hue", description="Weather-driven Hue lamp color")
    sub = parser.add_subparsers(dest="command", required=True)

    morning = sub.add_parser("morning", help="Run one weather->color cycle (cron entrypoint)")
    morning.add_argument("--lamp", help="Override the configured default lamp name")

    args = parser.parse_args(argv)
    config = load()

    if args.command == "morning":
        result = run_once(config, lamp=args.lamp)
        print(
            f"OK: '{result.lamp}' -> {result.decision.reason}; "
            f"xy={result.decision.xy} brightness={result.decision.brightness:.0f}"
        )
        return 0

    return 2  # unreachable — argparse enforces a valid command


if __name__ == "__main__":
    sys.exit(main())
