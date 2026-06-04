#!/usr/bin/env python3
"""AHSGR executive-assistant briefing CLI.

Usage:
    .venv/bin/python brief.py morning [--preview] [--force] [--since WINDOW]
    .venv/bin/python brief.py eod     [--preview] [--force] [--since WINDOW]
    .venv/bin/python brief.py channel test  [discord|slack|all]
    .venv/bin/python brief.py channel pause <discord|slack|all> <30m|2h|1d>

The scheduled launchd jobs call `morning` / `eod` with NO flags. The fabrication
gate (lib/briefing/brief.py:run_brief) suppresses generation+delivery whenever
data/context.md holds no grounded items — so the job is silent until grounded.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from rich.console import Console  # noqa: E402
from briefing.brief import run_brief  # noqa: E402
from briefing import delivery  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(prog="brief", description="AHSGR exec-assistant briefing")
    sub = parser.add_subparsers(dest="command", required=True)

    for bt in ("morning", "eod"):
        p = sub.add_parser(bt, help=f"generate the {bt} brief")
        p.add_argument("--preview", action="store_true", help="render only; do not deliver")
        p.add_argument("--force", action="store_true", help="bypass the fabrication gate (test only)")
        p.add_argument("--since", default=None, help="only include items since WINDOW")

    pc = sub.add_parser("channel", help="channel management")
    csub = pc.add_subparsers(dest="channel_command", required=True)
    csub.add_parser("test").add_argument("target", nargs="?", default="all")
    pp = csub.add_parser("pause")
    pp.add_argument("target")
    pp.add_argument("duration")

    args = parser.parse_args()
    console = Console()

    if args.command in ("morning", "eod"):
        run_brief(args.command, preview=args.preview, console=console,
                  force=args.force, since=args.since)
    elif args.command == "channel":
        if args.channel_command == "test":
            delivery.test_channel(args.target, console)
        else:
            delivery.pause_channel(args.target, args.duration, console)


if __name__ == "__main__":
    main()
