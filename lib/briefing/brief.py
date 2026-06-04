"""Brief generation + the fabrication gate.

THE GATE (the reason this port exists): a brief is generated and delivered ONLY
when `data/context.md` holds real, grounded items. Empty or placeholder context
=> suppressed BEFORE any LLM call or delivery. `forbid_fabrication` is a code
guarantee here, not a YAML comment.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import yaml
from dotenv import load_dotenv
from rich.console import Console

# Repo root: lib/briefing/brief.py -> parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")  # no-op if absent

BRIEF_CONFIG_DIR = REPO_ROOT / "config" / "brief"
CONTEXT_FILE = REPO_ROOT / "data" / "context.md"
PERSONA_FILE = BRIEF_CONFIG_DIR / "persona.md"
OLLAMA_TIMEOUT = 180  # seconds — local model can be slow on cold start

DEFAULT_PERSONA = (
    "You are the executive assistant for the AHSGR North Denver Chapter "
    "(American Historical Society of Germans from Russia). You write concise, "
    "accurate operational briefs for the chapter board. You report ONLY what is "
    "in the provided context — you never invent, infer, or pad."
)


def _ollama_chat_url() -> str:
    # Prefer an explicit full URL; otherwise derive from OLLAMA_HOST (matches .env.example).
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    return os.environ.get("OLLAMA_URL", f"{host}/api/chat")


def _ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "llama3.1:8b")


# ── Context + the grounding check ────────────────────────────────────────────

def load_context() -> str:
    if CONTEXT_FILE.exists():
        return CONTEXT_FILE.read_text(encoding="utf-8").strip()
    return ""


def _is_placeholder(line: str) -> bool:
    """True for blank/scaffolding/placeholder lines that are NOT grounded content."""
    s = line.strip()
    if not s:
        return True
    if s[0] in "#>" or s.startswith(("<!--", "-->", "---", "```")):
        return True
    if s.startswith(("*Last updated", "Update this file")):
        return True
    low = s.lower()
    # "No items.", "No calendar items added yet.", "No tasks added yet."
    if low.startswith("no ") and (low.endswith(".") or "yet" in low):
        return True
    return False


def grounded_items(context_text: str) -> list[str]:
    """Real content lines from context.md, with scaffolding/placeholders stripped.

    The fabrication gate keys off this: an empty list means there is nothing real
    to brief, so we must NOT call the model (it would confabulate)."""
    return [ln.strip() for ln in context_text.splitlines() if not _is_placeholder(ln)]


# ── Prompt assembly ──────────────────────────────────────────────────────────

def _load_schema(brief_type: str) -> dict:
    path = BRIEF_CONFIG_DIR / f"{brief_type}.yml"
    if not path.exists():
        raise SystemExit(f"[blocked] Brief spec missing: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_persona() -> str:
    if PERSONA_FILE.exists():
        return PERSONA_FILE.read_text(encoding="utf-8").strip()
    return DEFAULT_PERSONA


def _build_system_prompt(brief_type: str) -> str:
    schema = _load_schema(brief_type)
    sections = list(schema.get("sections", {}).keys())
    budget = schema.get("char_budget", 2400)
    label = schema.get("label", brief_type)
    section_list = "\n".join(f"- {s}" for s in sections)
    return (
        f"{_load_persona()}\n\n---\n\n"
        f"You are generating the **{label}**. Write clean Markdown. "
        f"Include only these sections, in order:\n{section_list}\n\n"
        f"Stay under {budget} characters total. Be direct and actionable. "
        "Use ONLY the items in the context below — do not invent, infer, or pad. "
        "If a listed section has no matching item in the context, write exactly "
        "`No items.` under it. Do not add sections not listed above."
    )


def _build_user_prompt(items: list[str], since: Optional[str]) -> str:
    now = datetime.now(timezone.utc).astimezone()
    parts = [f"Today is {now:%A, %Y-%m-%d} ({now:%H:%M} MT)."]
    if since:
        parts.append(f"Only include items from {since} onward.")
    parts.append("\n## Current Context (the ONLY source of truth)\n\n" + "\n".join(items))
    return "\n".join(parts)


def _call_ollama(system: str, user: str, console: Console) -> str:
    url = _ollama_chat_url()
    payload = {
        "model": _ollama_model(),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
    }
    try:
        resp = httpx.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
    except httpx.ConnectError:
        console.print(f"[bold red]✗[/] Cannot reach Ollama at {url} — is it running?")
        raise SystemExit(1)
    except httpx.TimeoutException:
        console.print(f"[bold red]✗[/] Ollama timed out after {OLLAMA_TIMEOUT}s — model may be loading.")
        raise SystemExit(1)
    except httpx.HTTPStatusError as exc:
        console.print(f"[bold red]✗[/] Ollama returned {exc.response.status_code}: {exc.response.text[:200]}")
        raise SystemExit(1)
    return resp.json()["message"]["content"]


def build_brief(brief_type: str, items: list[str], since: Optional[str], console: Console) -> str:
    now = datetime.now(timezone.utc).astimezone()
    model = _ollama_model()
    label = _load_schema(brief_type).get("label", brief_type)
    console.print(f"[dim]Calling {model} via Ollama on {len(items)} grounded item(s)…[/dim]")
    content = _call_ollama(_build_system_prompt(brief_type), _build_user_prompt(items, since), console)
    header = f"# AHSGR Exec Assistant — {label}\n**{now:%A, %Y-%m-%d}** — America/Denver"
    if since:
        header += f"  \n**Window:** since {since}"
    footer = f"\n\n---\n*Generated {now:%H:%M MT} | {model} | {len(items)} grounded item(s)*"
    return f"{header}\n\n{content}{footer}"


# ── Public entrypoint ────────────────────────────────────────────────────────

def run_brief(
    brief_type: str,
    preview: bool,
    console: Console,
    force: bool = False,
    since: Optional[str] = None,
    build: bool = True,
) -> None:
    """Generate + deliver a brief — only if there is grounded context.

    Fabrication gate: with no grounded items we log and HARD-RETURN before any
    LLM call or delivery. `force=True` is for explicit tests only and is never
    used by the scheduled jobs.
    """
    if build:
        from . import context_builder

        context_builder.build_context(console)

    items = grounded_items(load_context())

    if not items and not force:
        console.print(
            f"[yellow]∅ suppressed (forbid_fabrication): no grounded context in "
            f"{CONTEXT_FILE} — nothing generated, nothing delivered.[/]"
        )
        return
    if not items and force:
        console.print("[yellow]⚠ force: no grounded context; proceeding for test only.[/]")
        items = ["(forced test run — no real items)"]

    content = build_brief(brief_type, items, since, console)

    if preview:
        console.print(content)
        console.print("\n[dim](preview — not delivered)[/dim]")
        return

    from .delivery import deliver
    console.print(content)
    deliver(content, brief_type, console)
