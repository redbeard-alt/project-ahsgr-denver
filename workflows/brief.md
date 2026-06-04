# Workflow — Executive-Assistant Briefing

Generates the chapter's Morning Brief / EOD Recap from **grounded context only** and
delivers to Discord/Slack. Ported 2026-06-03 from a stranded clone whose copy delivered
hallucinated briefs to a live channel; see
`support/project-ahsgr-denver/INCIDENT_2026-06-03_brief-fabrication.md`.

## The fabrication gate (the whole point)
`data/context.md` is the **only** source of truth. `lib/briefing/brief.py:run_brief`
extracts grounded items (placeholders/scaffolding stripped). **No grounded items ⇒
suppressed: no Ollama call, no delivery.** This is enforced in code, not just declared in
spec YAML. Until Phase 2 wires live data (Gmail/Calendar MCP) into `data/context.md`, every
scheduled run correctly suppresses.

## Files
| Path | Role |
|---|---|
| `brief.py` (root) | argparse CLI entrypoint |
| `lib/briefing/brief.py` | generation + the gate |
| `lib/briefing/delivery.py` | Discord/Slack webhooks, routing, pause/test |
| `config/brief/{morning,eod}.yml` | brief schemas (sections, char budget) |
| `config/brief/channels.yml` | routing (primary=discord preview, no fallback) |
| `config/brief/failure_modes.yml` | policy (informational) |
| `config/brief/persona.md` | assistant persona / no-fabrication rules |
| `data/context.md` | live context (gitignored); the gate reads this |
| `launchd/com.ahsgr.brief.{morning,eod}.plist` | 06:00 / 17:00 weekday schedule |

## Run
```bash
.venv/bin/python brief.py morning --preview     # render only, never delivers
.venv/bin/python brief.py morning               # generate + deliver IF grounded; else suppress
.venv/bin/python brief.py channel test discord  # webhook smoke test
.venv/bin/python brief.py channel pause discord 2h
```

## `data/context.md` format
Freeform Markdown under labeled sections. A line is **grounded** if it is real content —
blank lines, headers (`#`/`>`), `---`, code fences, and `No … yet` / `No items.`
placeholders are ignored. Example of a grounded morning context:
```markdown
## Today's Calendar
- 9:00 AM MT: Board meeting (Zoom)
## Active Tasks
- Follow up with treasurer on the financial report
```

## Scheduling (Phase 2 — not enabled yet)
Do **not** register the launchd jobs until the gate is verified and a preview Discord channel
is wired (`DISCORD_WEBHOOK_URL` in `.env`). Then:
```bash
bash launchd/install.sh          # install (06:00 + 17:00 weekdays)
bash launchd/install.sh --unload # remove
```
Promote to the live channel only after Phase 2's promotion criteria: 7 consecutive runs incl.
≥1 silenced empty-day run AND ≥1 data-matched delivered brief.
