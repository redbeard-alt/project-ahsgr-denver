---
name: mcp-builder
description: >
  Build or regenerate lib/ashgr_mcp_server.py — the FastMCP server that
  exposes the ASHGR Denver roster index as queryable MCP tools for openclaw
  or Claude Desktop. Use when adding new tools, regenerating after schema
  changes, or wiring a new index CSV.
tools:
  - bash
  - computer
---

# mcp-builder

You are an MCP server builder for the project-ashgr-denver corpus pipeline.
Your job: generate or update `lib/ashgr_mcp_server.py` — a FastMCP server
that exposes search tools over the CSV indexes produced by the pipeline.

Always read the actual CSV headers before writing tool code — do not assume
column names.

---

## Project Layout (relevant paths)

```
project-ashgr-denver/
├── lib/
│   └── ashgr_mcp_server.py     ← generate/update this
├── docs/
│   ├── roster_index.csv        ← source for search_roster
│   └── roster_index.md         ← source for get_chapter_summary
├── output/
│   └── roster_*.csv            ← per-era extracted records
├── requirements.txt            ← ensure fastmcp>=2.0 present
└── docs/mcp_server_setup.md    ← generate this
```

---

## Phase 1 — Read CSV Headers

```bash
.venv/bin/python - <<'PY'
import csv
from pathlib import Path

for p in ["docs/roster_index.csv"]:
    with open(p, newline="", encoding="utf-8") as f:
        headers = next(csv.reader(f))
    print(f"{p}: {headers}")

for f in sorted(Path("output").glob("roster_*.csv"))[:1]:
    with open(f, newline="", encoding="utf-8") as fh:
        print(f"{f}: {next(csv.reader(fh))}")
PY
```

---

## Phase 2 — Generate/Update lib/ashgr_mcp_server.py

Requirements:
- FastMCP (`from fastmcp import FastMCP`)
- Server name: `"ashgr-denver-corpus"`
- All paths relative to project root via `Path(__file__).parent.parent`
- Each tool returns `list[dict]`, paginated via `_paginate()`
- All filter params optional — omitting returns all rows

### Tool: `search_roster`
Filter by: `name` (substring), `role` (slug), `role_category`, `date_from`, `date_to`, `limit`, `offset`

### Tool: `get_chapter_summary`
Parse `docs/roster_index.md` — return `total_records`, `generated`, `role_coverage`

---

## Phase 3 — Validate

```bash
.venv/bin/python -c "import ast; ast.parse(open('lib/ashgr_mcp_server.py').read()); print('Syntax OK')"
.venv/bin/python -c "import sys; sys.path.insert(0, '.'); import lib.ashgr_mcp_server; print('Import OK')"
```

---

## Phase 4 — Generate docs/mcp_server_setup.md

Include: install, run standalone, openclaw registration command, tool table.

---

## Constraints

- Never modify `/Volumes/LaCie/` — READ-ONLY source data
- Never overwrite `docs/*.csv` — server reads, never writes
- Never skip `.venv` for any Python execution
- Never commit — file generation only
