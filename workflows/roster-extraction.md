# Workflow: Roster Extraction

Extract board and officer records from a newsletter issue into the roster index.

## Trigger

New newsletter added to `data/`, or a historical issue needs parsing.

## Steps

1. Place source file in `data/` (PDF or .md)
2. Run `lib/extractor.py` against the file — see skill `ashgr/roster-extraction`
3. Review extracted records for name/role accuracy
4. Write to `output/roster_YYYY.csv`
5. Run `make build` to rebuild `docs/roster_index.csv`
6. Run `make test` to validate
7. Promote roster CSV to `data-hub-ashgr-denver/board/roster/` via:

```bash
cd ~/Laboratory/data-hub-ashgr-denver
.venv/bin/python cli.py promote \
  ~/Laboratory/project-ashgr-denver/output/roster_YYYY.csv \
  --topic board/roster \
  --source-agent project-ashgr-denver
```

## Data flow

```
data/<newsletter>.pdf
  → lib/extractor.py
  → output/roster_YYYY.csv
  → build_roster_index.py
  → docs/roster_index.csv  (MCP server source)
  → data-hub-ashgr-denver/board/roster/  (promoted, indexed)
```
