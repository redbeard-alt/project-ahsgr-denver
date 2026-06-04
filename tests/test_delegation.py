from pathlib import Path

import pytest

from lib.delegation import audio_command, newsletter_command


def test_audio_command_uses_env_path(monkeypatch):
    monkeypatch.setenv("AUDIO_AGENT_PATH", "/tmp/audio-agent")
    assert audio_command("/tmp/meeting.m4a") == [
        "make",
        "-C",
        "/tmp/audio-agent",
        "run",
        "FILE=/tmp/meeting.m4a",
        "PROJECT=ahsgr",
    ]


def test_newsletter_send_defaults_to_dry_run(monkeypatch):
    monkeypatch.setenv("NEWSLETTER_AGENT_PATH", "/tmp/newsletter-agent")
    cmd = newsletter_command("send", "~/issue")
    assert cmd[1] == "/tmp/newsletter-agent/cli.py"
    assert cmd[-2:] == ["--issue-dir", str(Path("~/issue").expanduser())]
    assert "--live" not in cmd


def test_newsletter_live_requires_confirm(monkeypatch):
    monkeypatch.setenv("NEWSLETTER_AGENT_PATH", "/tmp/newsletter-agent")
    with pytest.raises(PermissionError):
        newsletter_command("send", "/tmp/issue", live=True)
    assert newsletter_command("send", "/tmp/issue", live=True, confirm_live=True)[-1] == "--live"
