---
name: roster-extraction
description: Extract board and officer records from ASHGR newsletters or PDFs into output/roster_YYYY.csv
---

# roster-extraction

Extract names and roles from ASHGR source documents into the roster schema.

## When to use

- A new newsletter PDF or markdown has been loaded into `data/`
- A historical issue needs to be parsed for officer changes
- Bulk extraction of a year's worth of newsletters

## Steps

1. **Identify source file** in `data/` (PDF or .md)

2. **Run extractor**
```bash
.venv/bin/python - <<'PY'
from pathlib import Path
from lib.extractor import extract_from_file

results = extract_from_file(Path("data/<filename>"), start_date="YYYY-MM-DD")
for r in results:
    print(r)
PY
```

3. **Review output** — verify names and roles are correctly extracted

4. **Write to output CSV**
```bash
.venv/bin/python - <<'PY'
import csv
from pathlib import Path
from lib.extractor import extract_from_file
from lib.normalizer import make_record

records = extract_from_file(Path("data/<filename>"), start_date="YYYY-MM-DD")
out = Path("output/roster_YYYY.csv")
schema = ["name","role","role_category","start_date","end_date","source_file","source_page","notes"]
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=schema)
    w.writeheader()
    w.writerows(records)
print(f"Wrote {len(records)} records to {out}")
PY
```

5. **Rebuild index** — `make build`

6. **Verify** — `make build-dry` then `make test`

## Edge cases

- See `docs/KNOWN_EDGE_CASES.md` before investigating any anomaly
- Name+role on same line: adjust `_OFFICER_LINE` regex in `lib/extractor.py`
- Handwritten or scanned PDFs: OCR first via research-agent before extracting
