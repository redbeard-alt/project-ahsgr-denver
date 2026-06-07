"""Brief delivery — Discord/Slack webhooks, channel routing, pause/test.

Delivery is reached only after the fabrication gate in brief.run_brief has
already confirmed grounded content. Webhook URLs come from a gitignored .env;
missing URL => skip (never crash). Channel state lives under data/ (gitignored).
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone

import httpx
import yaml
from rich.console import Console

from .brief import REPO_ROOT, BRIEF_CONFIG_DIR

CHANNELS_SPEC = BRIEF_CONFIG_DIR / "channels.yml"
CHANNEL_STATE = REPO_ROOT / "data" / "briefing-channel-state.json"  # gitignored (data/)
_DISCORD_LIMIT = 1900  # Discord hard cap is 2000; headroom for code fences

_ENV_VAR = {"discord": "DISCORD_WEBHOOK_URL", "slack": "SLACK_WEBHOOK_URL"}


# ── Routing config + channel state ───────────────────────────────────────────

def _load_routing() -> dict:
    if not CHANNELS_SPEC.exists():
        return {}
    return yaml.safe_load(CHANNELS_SPEC.read_text(encoding="utf-8")) or {}


def _load_channel_state() -> dict:
    if CHANNEL_STATE.exists():
        return json.loads(CHANNEL_STATE.read_text(encoding="utf-8"))
    return {}


def _save_channel_state(state: dict) -> None:
    CHANNEL_STATE.parent.mkdir(parents=True, exist_ok=True)
    CHANNEL_STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _is_channel_paused(target: str) -> tuple[bool, str]:
    state = _load_channel_state()
    paused_until = state.get(f"paused_until_{target}")
    if paused_until:
        if datetime.now(timezone.utc) < datetime.fromisoformat(paused_until):
            return True, paused_until
        del state[f"paused_until_{target}"]  # expired
        _save_channel_state(state)
    return False, ""


# ── Webhook senders ──────────────────────────────────────────────────────────

def _post_discord(content: str, console: Console) -> bool:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        console.print("[yellow]⚠[/]  DISCORD_WEBHOOK_URL not set — skipping Discord.")
        return False
    chunks = [content[i:i + _DISCORD_LIMIT] for i in range(0, len(content), _DISCORD_LIMIT)]
    try:
        for chunk in chunks:
            httpx.post(url, json={"content": chunk}, timeout=15).raise_for_status()
    except httpx.HTTPStatusError as exc:
        console.print(f"[bold red]✗[/] Discord returned {exc.response.status_code}: {exc.response.text[:200]}")
        return False
    except httpx.RequestError as exc:
        console.print(f"[bold red]✗[/] Discord request failed: {exc}")
        return False
    return True


def _post_slack(content: str, console: Console) -> bool:
    url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not url:
        console.print("[yellow]⚠[/]  SLACK_WEBHOOK_URL not set — skipping Slack.")
        return False
    try:
        httpx.post(url, json={"text": content}, timeout=15).raise_for_status()
    except httpx.HTTPStatusError as exc:
        console.print(f"[bold red]✗[/] Slack returned {exc.response.status_code}: {exc.response.text[:200]}")
        return False
    except httpx.RequestError as exc:
        console.print(f"[bold red]✗[/] Slack request failed: {exc}")
        return False
    return True


_SENDERS = {"discord": _post_discord, "slack": _post_slack}


# ── Public delivery API ──────────────────────────────────────────────────────

def deliver(content: str, brief_type: str, console: Console) -> None:
    """Deliver to the primary channel for this brief, falling back if it fails.
    Respects pause state. Missing webhook URL is a skip, not a crash."""
    routing = _load_routing()
    route = routing.get("routing", {}).get("work", {})
    primary = route.get("primary", "discord")
    fallback = route.get("fallback", "")

    for target in ([primary, fallback] if fallback else [primary]):
        if not target:
            continue
        paused, until = _is_channel_paused(target)
        if paused:
            console.print(f"[yellow]⏸[/]  {target} paused until {until} — skipping.")
            continue
        sender = _SENDERS.get(target)
        if not sender:
            console.print(f"[yellow]⚠[/]  Unknown channel '{target}' — skipping.")
            continue
        if sender(content, console):
            console.print(f"[bold green]✓[/] Delivered to {target}.")
            return
        if target == primary and fallback:
            console.print(f"[dim]Primary failed — trying fallback ({fallback})…[/dim]")


def test_channel(target: str, console: Console) -> None:
    routing = _load_routing()
    channels = routing.get("channels", {})
    targets = list(channels.keys()) if target == "all" else [target]
    for ch in targets:
        dest = channels.get(ch, {}).get("destination", "(not configured)")
        url = os.environ.get(_ENV_VAR.get(ch, ""), "").strip()
        console.print(f"[bold cyan]➤[/]  {ch}: destination={dest}")
        if not url:
            console.print(f"[yellow]⚠[/]  {_ENV_VAR.get(ch, '?')} not set — add it to .env to enable.")
            continue
        sender = _SENDERS.get(ch)
        if not sender:
            console.print(f"[yellow]⚠[/]  No sender for {ch}.")
            continue
        now = datetime.now(timezone.utc).astimezone()
        payload = (
            f"🧪 **AHSGR Exec Assistant — channel test**\n"
            f"Channel: {ch} | Destination: {dest}\nTime: {now:%Y-%m-%d %H:%M MT}\n"
            f"Status: delivery pipeline ok"
        )
        ok = sender(payload, console)
        console.print(
            f"[bold green]✓[/] Test delivered to {ch}." if ok
            else f"[bold red]✗[/] Test delivery to {ch} failed — check webhook URL."
        )


def pause_channel(target: str, duration: str, console: Console) -> None:
    match = re.fullmatch(r"(\d+)([mhd])", duration.strip())
    if not match:
        console.print(f"[bold red]✗[/] Invalid duration '{duration}'. Use 30m, 2h, 1d.")
        raise SystemExit(1)
    amount, unit = int(match.group(1)), match.group(2)
    delta = {"m": timedelta(minutes=amount), "h": timedelta(hours=amount), "d": timedelta(days=amount)}[unit]
    until = (datetime.now(timezone.utc) + delta).isoformat()
    state = _load_channel_state()
    for ch in (["discord", "slack"] if target == "all" else [target]):
        state[f"paused_until_{ch}"] = until
    _save_channel_state(state)
    console.print(f"[bold green]✓[/] {target} paused until {until}")
