"""Tests for grounded briefing context and the fabrication gate."""

import io
import sys
from pathlib import Path

from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from briefing import context_builder  # noqa: E402
from briefing.brief import grounded_items, run_brief  # noqa: E402


class _Executable:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _CalendarEvents:
    def __init__(self, payload):
        self.payload = payload
        self.kwargs = None

    def list(self, **kwargs):
        self.kwargs = kwargs
        return _Executable(self.payload)


class _CalendarService:
    def __init__(self, payload):
        self._events = _CalendarEvents(payload)

    def events(self):
        return self._events


class _GmailMessages:
    def __init__(self, ids, details):
        self.ids = ids
        self.details = details

    def list(self, **_kwargs):
        return _Executable({"messages": [{"id": msg_id} for msg_id in self.ids]})

    def get(self, **kwargs):
        return _Executable(self.details[kwargs["id"]])


class _GmailUsers:
    def __init__(self, messages):
        self._messages = messages

    def messages(self):
        return self._messages


class _GmailService:
    def __init__(self, ids, details):
        self._users = _GmailUsers(_GmailMessages(ids, details))

    def users(self):
        return self._users


def _console():
    return Console(file=io.StringIO(), force_terminal=False, width=120)


def _patch_context_file(monkeypatch, tmp_path):
    context_file = tmp_path / "context.md"
    monkeypatch.setattr(context_builder, "CONTEXT_FILE", context_file)
    import briefing.brief as brief

    monkeypatch.setattr(brief, "CONTEXT_FILE", context_file)
    return context_file


def test_context_builder_writes_google_items_as_grounded(monkeypatch, tmp_path):
    context_file = _patch_context_file(monkeypatch, tmp_path)
    cal = _CalendarService(
        {
            "items": [
                {
                    "summary": "Board packet review",
                    "location": "Zoom",
                    "start": {"dateTime": "2026-06-04T09:30:00-06:00"},
                }
            ]
        }
    )
    gmail = _GmailService(
        ["abc123"],
        {
            "abc123": {
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Treasurer report"},
                        {"name": "From", "value": "Treasurer <treasurer@example.org>"},
                    ]
                }
            }
        },
    )

    def fake_service(api, _version, _scopes):
        return cal if api == "calendar" else gmail

    monkeypatch.setattr(context_builder, "_google_service", fake_service)

    assert context_builder.build_context(_console()) == 2
    items = grounded_items(context_file.read_text(encoding="utf-8"))

    assert "- 09:30 MT: Board packet review (Zoom)" in items
    assert "- reply: Treasurer report — Treasurer <treasurer@example.org>" in items


def test_empty_google_pull_writes_placeholders_and_run_brief_suppresses(monkeypatch, tmp_path):
    _patch_context_file(monkeypatch, tmp_path)
    cal = _CalendarService({"items": []})
    gmail = _GmailService([], {})

    def fake_service(api, _version, _scopes):
        return cal if api == "calendar" else gmail

    monkeypatch.setattr(context_builder, "_google_service", fake_service)

    def fail_ollama(*_args, **_kwargs):
        raise AssertionError("Ollama must not be called without grounded items")

    import briefing.brief as brief

    monkeypatch.setattr(brief, "_call_ollama", fail_ollama)
    run_brief("morning", preview=True, console=_console())

    assert grounded_items(brief.load_context()) == []


def test_placeholder_context_has_no_grounded_items():
    context = """
    # AHSGR Briefing Context
    *Last updated 2026-06-04 08:00 MT*

    ## calendar
    No items.
    ## tasks
    No tasks added yet.
    ## email
    No items.
    """

    assert grounded_items(context) == []
