#!/usr/bin/env python3
"""AHSGR chapter-president orchestrator delegation CLI."""
from __future__ import annotations

import argparse

from lib.delegation import run_audio, run_newsletter


def main() -> None:
    parser = argparse.ArgumentParser(description="Delegate AHSGR work to service agents.")
    sub = parser.add_subparsers(dest="kind", required=True)

    audio = sub.add_parser("audio", help="Transcribe audio via $AUDIO_AGENT_PATH")
    audio.add_argument("file")

    newsletter = sub.add_parser("newsletter", help="Run newsletter-agent draft/render/send")
    newsletter.add_argument("step", choices=["draft", "render", "send"])
    newsletter.add_argument("--issue-dir", default="~/Laboratory/client-unsere-zeitung/issues/volume-38-issue-1")
    newsletter.add_argument("--live", action="store_true", help="Pass --live to newsletter-agent send")
    newsletter.add_argument("--confirm-live", action="store_true", help="Required with --live")

    args = parser.parse_args()
    if args.kind == "audio":
        run_audio(args.file)
    elif args.kind == "newsletter":
        run_newsletter(args.step, args.issue_dir, live=args.live, confirm_live=args.confirm_live)


if __name__ == "__main__":
    main()
