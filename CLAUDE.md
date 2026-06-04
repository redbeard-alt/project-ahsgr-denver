# CLAUDE.md — project-ashgr-denver

## Purpose

Corpus and MCP server for ASHGR North Denver Chapter (American Heritage Society of Germans from Russia). Tracks board and officer roles over time — president, vice president, secretary, treasurer, directors, newsletter editor, marketing director, and member committee chair — extracted from newsletters and member directories.

Mirrors the project-svvsd architecture: extract → normalize → CSV index → FastMCP search tools → openclaw.

**OpenClaw client slug:** `ahsgr-north-denver`
**Client type:** `nonprofit-chapter`

## Data Hub

Promotes outputs to `/Volumes/BJH/data-hub-ahsgr/` (`~/Laboratory/data-hub-ahsgr` symlink):

```bash
cd ~/Laboratory/data-hub-ahsgr
.venv/bin/python cli.py promote <file> --topic board/roster --source-agent project-ahsgr-denver
make build
```

## Project Working Folder

`projects/ahsgr-north-denver/` — client outputs, working files, archives, memory:

- `working/` — in-progress files
- `output/` — completed deliverables (promote to data-hub when ready)
- `archive/` — frozen versioned snapshots
- `memory/` — persistent project notes and decisions across sessions

## Architecture

```
data/               source documents (newsletters, PDFs) — gitignored
lib/
  extractor.py      extract name/role records from text or PDF
  normalizer.py     coerce to roster schema (Last, First / role slug)
  ashgr_mcp_server.py  FastMCP server: search_roster, get_chapter_summary
config/
  format_rules.yml  canonical role names and normalization rules
output/
  roster_YYYY.csv   per-era extracted records
docs/
  roster_index.csv  unified index (built by build_roster_index.py)
  roster_index.md   coverage summary
  KNOWN_EDGE_CASES.md
build_roster_index.py  aggregates output/ → docs/
```

## Dev Commands

```bash
make install        # python3.12 venv + deps
make build          # rebuild docs/roster_index.csv
make build-dry      # dry-run
make run            # start FastMCP server (openclaw registers this)
make test           # pytest
make lint           # ruff
```

## Gotchas

- **Python 3.12 required** — matches research-agent and project-svvsd
- **data/ is gitignored** — source newsletters never committed
- **output/ CSVs are gitignored by default** — commit only after review
- **Schema is frozen** after first live ship — do not reorder columns in normalizer.py
- Always dry-run before live build: `make build-dry`

## OpenClaw Registration

The MCP server registers as `ashgr-denver-corpus` in openclaw. Run:

```bash
openclaw gateway register --name ashgr-denver-corpus --command ".venv/bin/python lib/ashgr_mcp_server.py" --cwd ~/Laboratory/project-ashgr-denver
```

Or configure via `openclaw-agent`:

```bash
cd ~/Laboratory/openclaw-agent
python cli.py configure --client ahsgr-north-denver
```

## Claude Skills

Project-unique skills live in `.claude/skills/ashgr/`. Shared skills are served via `additionalDirectories` from `config-ai-agent/skills/` — no local copies needed.

| Skill | Trigger phrases |
| --- | --- |
| `ashgr/ingest-journals` | "ingest journal PDFs", "promote journals", "add new Unsere Zeitung issues" |
| `ashgr/roster-extraction` | "extract roster", "update member list", "parse chapter roster" |
| `rag/data-hub-promote` | "promote to data hub", "file this", "push to data-hub-ahsgr" |
| `rag/lancedb-search` | "search the journal archive", "find articles on", "RAG search", "semantic search" |
| `scraping/bright-data-mcp` | "fetch this URL", "look up online", any live web lookup |
| `discover-urls` | "search for", "find articles about", URL discovery |
| `memory/prior-context-check` | "what do I know about", "check prior context", "have I seen this member" |
