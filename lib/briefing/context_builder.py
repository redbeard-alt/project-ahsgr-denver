"""Build grounded briefing context from read-only Google sources.

This module writes ``data/context.md``. It does not generate, send, or infer
briefing content; the fabrication gate in ``brief.py`` remains the delivery
authority.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from rich.console import Console

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTEXT_FILE = REPO_ROOT / "data" / "context.md"
CLIENT_CREDENTIALS_FILE = REPO_ROOT / "clients" / "ahsgr-north-denver" / "google_credentials.json"
BOARD_INDEX_DB = REPO_ROOT / "docs" / "board_index.db"
MT = ZoneInfo("America/Denver")

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
TOKEN_URI = "https://oauth2.googleapis.com/token"

load_dotenv(REPO_ROOT / ".env")  # no-op if absent

LOGGER = logging.getLogger(__name__)
GOOGLE_READONLY_SCOPES = [GMAIL_READONLY_SCOPE, CALENDAR_READONLY_SCOPE]


def build_context(console: Console) -> int:
    """Pull live sources, write ``data/context.md``, and return grounded count."""
    calendar: list[str] = []
    email: list[str] = []
    tasks: list[str] = []
    research: list[str] = []
    flags: list[str] = []

    try:
        tasks = _board_action_items()
    except Exception as exc:  # noqa: BLE001 - scheduled runs must preserve the fabrication gate.
        LOGGER.error("Board action-item context source failed", exc_info=True)
        console.print(f"[yellow]board action context unavailable; see logs: {exc}[/]")

    try:
        calendar = _calendar_next(_google_service("calendar", "v3", GOOGLE_READONLY_SCOPES))
    except Exception as exc:  # noqa: BLE001 - scheduled runs must preserve the fabrication gate.
        LOGGER.error("Calendar context source failed", exc_info=True)
        console.print(f"[yellow]calendar context unavailable; see logs: {exc}[/]")

    try:
        email = _gmail_followups(_google_service("gmail", "v1", GOOGLE_READONLY_SCOPES))
    except Exception as exc:  # noqa: BLE001 - scheduled runs must preserve the fabrication gate.
        LOGGER.error("Gmail context source failed", exc_info=True)
        console.print(f"[yellow]gmail context unavailable; see logs: {exc}[/]")

    grounded_count = _write_context(calendar, tasks, email, research, flags)
    console.print(f"[dim]Wrote {CONTEXT_FILE} with {grounded_count} grounded item(s).[/dim]")
    return grounded_count


def _google_service(api: str, version: str, scopes: list[str]) -> Any:
    """Return an authenticated Google API service using the repo OAuth config."""
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = _credentials_from_env(scopes) or _credentials_from_file(scopes)
    if not creds:
        raise FileNotFoundError(
            "Google OAuth credentials missing. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN in .env, or provide "
            f"{CLIENT_CREDENTIALS_FILE}."
        )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError("Google OAuth credentials are invalid and have no refresh token.")

    return build(api, version, credentials=creds, cache_discovery=False)


def _credentials_from_env(scopes: list[str]) -> Any | None:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        return None

    from google.oauth2.credentials import Credentials

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=os.getenv("GOOGLE_TOKEN_URI", TOKEN_URI),
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )


def _credentials_from_file(scopes: list[str]) -> Any | None:
    if not CLIENT_CREDENTIALS_FILE.exists():
        return None

    from google.oauth2.credentials import Credentials

    data = json.loads(CLIENT_CREDENTIALS_FILE.read_text(encoding="utf-8"))
    if data.get("type") == "authorized_user":
        return Credentials.from_authorized_user_info(data, scopes)

    payload = data.get("installed") or data.get("web") or data
    refresh_token = payload.get("refresh_token") or os.getenv("GOOGLE_REFRESH_TOKEN")
    if not refresh_token:
        raise RuntimeError(
            f"{CLIENT_CREDENTIALS_FILE} has client credentials but no refresh token. "
            "Add GOOGLE_REFRESH_TOKEN to .env or store an authorized_user JSON."
        )

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=payload.get("token_uri", TOKEN_URI),
        client_id=payload.get("client_id"),
        client_secret=payload.get("client_secret"),
        scopes=scopes,
    )


def _calendar_next(cal: Any, hours: int = 48) -> list[str]:
    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=hours)
    response = (
        cal.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    items: list[str] = []
    for event in response.get("items", []):
        summary = event.get("summary", "(untitled event)")
        location = event.get("location")
        start = event.get("start", {})
        raw_start = start.get("dateTime") or start.get("date")
        when = _format_calendar_time(raw_start)
        suffix = f" ({location})" if location else ""
        items.append(f"- {when}: {summary}{suffix}")
    return items


def _gmail_followups(gmail: Any) -> list[str]:
    response = (
        gmail.users()
        .messages()
        .list(userId="me", q="is:unread (is:important OR is:starred) newer_than:2d")
        .execute()
    )

    items: list[str] = []
    for message in response.get("messages", []):
        detail = (
            gmail.users()
            .messages()
            .get(userId="me", id=message["id"], format="metadata", metadataHeaders=["Subject", "From"])
            .execute()
        )
        headers = {
            header.get("name", "").lower(): header.get("value", "")
            for header in detail.get("payload", {}).get("headers", [])
        }
        subject = _decode_header(headers.get("subject") or "(no subject)")
        sender = _decode_header(headers.get("from") or "(unknown sender)")
        items.append(f"- reply: {subject} — {sender}")
    return items


def _board_action_items(limit: int = 8) -> list[str]:
    db_path = Path(os.environ.get("AHSGR_BOARD_INDEX_DB", BOARD_INDEX_DB))
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT item_text, document_path, doc_date
            FROM action_items
            WHERE status = 'open'
            ORDER BY doc_date DESC, id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [
        f"- board action: {row['item_text']} ({row['doc_date'] or row['document_path']})"
        for row in rows
    ]


def _write_context(
    calendar: list[str],
    tasks: list[str],
    email: list[str],
    research: list[str],
    flags: list[str],
) -> int:
    sections = {
        "calendar": calendar,
        "tasks": tasks,
        "email": email,
        "research": research,
        "flags": flags,
    }
    now = datetime.now(timezone.utc).astimezone(MT)
    lines = [
        "# AHSGR Briefing Context",
        f"*Last updated {now:%Y-%m-%d %H:%M MT}*",
        "",
    ]

    grounded_count = 0
    for label, items in sections.items():
        lines.append(f"## {label}")
        if items:
            lines.extend(items)
            grounded_count += len(items)
        else:
            lines.append("No items.")
        lines.append("")

    CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return grounded_count


def _format_calendar_time(raw_start: str | None) -> str:
    if not raw_start:
        return "time unknown MT"
    if "T" not in raw_start:
        return raw_start
    dt = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
    return f"{dt.astimezone(MT):%H:%M MT}"


def _decode_header(value: str) -> str:
    return str(make_header(decode_header(value)))
