#!/usr/bin/env python3
"""Build docs/roster_index.csv from all extracted output/ CSVs.

Usage:
    .venv/bin/python build_roster_index.py [--dry-run]
"""

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path("output")
DOCS = Path("docs")
INDEX_CSV = DOCS / "roster_index.csv"
INDEX_MD = DOCS / "roster_index.md"

SCHEMA = ["name", "role", "role_category", "start_date", "end_date", "source_file", "source_page", "notes"]


def load_all_records() -> list[dict]:
    records = []
    for f in sorted(OUTPUT.glob("roster_*.csv")):
        with open(f, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                records.append({k: row.get(k, "") for k in SCHEMA})
    return records


def write_csv(records: list[dict], dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would write {len(records)} rows to {INDEX_CSV}")
        return
    with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA)
        writer.writeheader()
        writer.writerows(records)
    print(f"✓ {INDEX_CSV}  ({len(records)} records)")


def write_md(records: list[dict], dry_run: bool) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    by_cat: dict[str, int] = {}
    for r in records:
        cat = r.get("role_category", "unknown")
        by_cat[cat] = by_cat.get(cat, 0) + 1

    rows_md = "\n".join(
        f"| {cat} | {count} | newsletter |"
        for cat, count in sorted(by_cat.items())
    )

    md = f"""# ASHGR Denver Roster Index

**Generated:** {now}
**Total records:** {len(records)}
**Source:** newsletter + member directory

## Coverage

| Role Category | Count | Source |
|---|---|---|
{rows_md}

Run `python build_roster_index.py` to regenerate.
"""
    if dry_run:
        print(f"[dry-run] would write {INDEX_MD}")
        return
    INDEX_MD.write_text(md, encoding="utf-8")
    print(f"✓ {INDEX_MD}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    records = load_all_records()
    print(f"Loaded {len(records)} records from {OUTPUT}/")
    write_csv(records, args.dry_run)
    write_md(records, args.dry_run)


if __name__ == "__main__":
    main()
