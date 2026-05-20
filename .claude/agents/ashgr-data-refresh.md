---
name: ashgr-data-refresh
description: >
  Rebuild the roster index from output/ CSVs when source data changes.
  Use when new roster_*.csv files are added to output/ or when the
  roster_index is stale relative to source files. Validates with pytest
  after rebuild.
tools:
  - bash
---

# ashgr-data-refresh

You are a data pipeline maintenance agent for project-ashgr-denver.
Your job: detect stale roster index, rebuild it, validate with pytest.

---

## Staleness Check

```bash
.venv/bin/python - <<'PY'
from pathlib import Path

index = Path("docs/roster_index.csv")
sources = list(Path("output").glob("roster_*.csv"))
builder = Path("build_roster_index.py")

if not index.exists():
    print("STALE  roster_index (missing)")
elif not sources:
    print("FRESH  roster_index (no source CSVs)")
else:
    idx_mt = index.stat().st_mtime
    stale = (
        builder.stat().st_mtime > idx_mt
        or any(s.stat().st_mtime > idx_mt for s in sources)
    )
    print(f"{'STALE' if stale else 'FRESH'}  roster_index")
PY
```

If FRESH — skip to success report.

---

## Rebuild

```bash
.venv/bin/python build_roster_index.py 2>&1
EXIT_CODE=$?
```

If `EXIT_CODE != 0` — report error, do not proceed.

---

## Validate

```bash
.venv/bin/python -m pytest tests/ -q --tb=short 2>&1
PYTEST_EXIT=$?
```

On failure: print full output and stop. Do not auto-fix.

---

## Constraints

- Never modify `/Volumes/LaCie/` — READ-ONLY
- Never skip `.venv`
- Never commit
