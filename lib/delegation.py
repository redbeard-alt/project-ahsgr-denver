"""Subprocess delegation helpers for AHSGR service agents."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _agent_path(env_name: str, default: Path) -> Path:
    return Path(os.environ.get(env_name, default)).expanduser()


def audio_command(audio_file: str, project: str = "ahsgr") -> list[str]:
    """Return the audio-agent subprocess command for one audio file."""
    audio_agent = _agent_path("AUDIO_AGENT_PATH", Path.home() / "Laboratory" / "audio-agent")
    return ["make", "-C", str(audio_agent), "run", f"FILE={audio_file}", f"PROJECT={project}"]


def run_audio(audio_file: str) -> subprocess.CompletedProcess:
    """Delegate an AHSGR audio transcription to audio-agent."""
    return subprocess.run(audio_command(audio_file), check=True)


def newsletter_command(
    step: str,
    issue_dir: str,
    live: bool = False,
    confirm_live: bool = False,
) -> list[str]:
    """Return a newsletter-agent CLI command.

    Live sends require both ``live=True`` and ``confirm_live=True``. The default
    path is dry-run/draft-safe.
    """
    if step not in {"draft", "render", "send"}:
        raise ValueError("newsletter step must be one of: draft, render, send")
    if live and not confirm_live:
        raise PermissionError("newsletter --live requires explicit --confirm-live")

    newsletter_agent = _agent_path("NEWSLETTER_AGENT_PATH", Path.home() / "Laboratory" / "newsletter-agent")
    resolved_issue_dir = str(Path(issue_dir).expanduser())
    agent_python = newsletter_agent / ".venv" / "bin" / "python"
    python = str(agent_python) if agent_python.exists() else sys.executable
    cmd = [python, str(newsletter_agent / "cli.py"), step]
    if step in {"render", "send"}:
        cmd.extend(["--issue-dir", resolved_issue_dir])
    if step == "send" and live:
        cmd.append("--live")
    return cmd


def run_newsletter(step: str, issue_dir: str, live: bool = False, confirm_live: bool = False) -> subprocess.CompletedProcess:
    """Delegate a newsletter step to newsletter-agent."""
    resolved_issue_dir = str(Path(issue_dir).expanduser())
    env = os.environ.copy()
    env.setdefault("ISSUE_DIR", resolved_issue_dir)
    env.setdefault("PROJECT_DIR", str(Path.home() / "Laboratory" / "client-unsere-zeitung"))
    return subprocess.run(newsletter_command(step, resolved_issue_dir, live=live, confirm_live=confirm_live), env=env, check=True)
