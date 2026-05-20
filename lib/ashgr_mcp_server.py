"""
FastMCP server — ashgr-denver-corpus

Tools:
  search_roster      Search officer/board records (docs/roster_index.csv)
  get_chapter_summary  Coverage stats from docs/roster_index.md
"""

import csv
import re
from pathlib import Path

from fastmcp import FastMCP

ROOT = Path(__file__).parent.parent

mcp = FastMCP("ashgr-denver-corpus")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _in_range(date_str: str, date_from: str, date_to: str) -> bool:
    if date_from and date_str and date_str < date_from:
        return False
    if date_to and date_str and date_str > date_to:
        return False
    return True


def _paginate(results: list[dict], limit: int, offset: int) -> list[dict]:
    total = len(results)
    page = results[offset: offset + limit] if limit > 0 else results[offset:]
    sentinel: dict = {
        "_meta": True,
        "_total": total,
        "_offset": offset,
        "_returned": len(page),
    }
    if limit > 0:
        sentinel["_limit"] = limit
        sentinel["_has_more"] = (offset + len(page)) < total
    return page + [sentinel]


# ---------------------------------------------------------------------------
# Tool 1: search_roster
# ---------------------------------------------------------------------------

@mcp.tool()
def search_roster(
    name: str = "",
    role: str = "",
    role_category: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 0,
    offset: int = 0,
) -> list[dict]:
    """Search ASHGR Denver officer and board records.

    Args:
        name: Partial name match (case-insensitive).
        role: Exact role slug (e.g. newsletter_editor, president).
        role_category: Filter by category: board | officers.
        date_from: ISO date — earliest start_date to include.
        date_to: ISO date — latest start_date to include.
        limit: Max rows to return (0 = all).
        offset: Pagination offset.
    """
    rows = _load_csv(ROOT / "docs" / "roster_index.csv")
    out = []
    for row in rows:
        if name and name.lower() not in row.get("name", "").lower():
            continue
        if role and role.lower() not in row.get("role", "").lower():
            continue
        if role_category and role_category.lower() != row.get("role_category", "").lower():
            continue
        if not _in_range(row.get("start_date", ""), date_from, date_to):
            continue
        out.append(row)
    return _paginate(out, limit, offset)


# ---------------------------------------------------------------------------
# Tool 2: get_chapter_summary
# ---------------------------------------------------------------------------

@mcp.tool()
def get_chapter_summary() -> dict:
    """Return ASHGR Denver roster coverage stats from docs/roster_index.md."""
    md_path = ROOT / "docs" / "roster_index.md"
    if not md_path.exists():
        return {"error": "roster_index.md not found"}

    text = md_path.read_text(encoding="utf-8")

    generated = re.search(r"\*\*Generated:\*\*\s*(.+)", text)
    total = re.search(r"\*\*Total records:\*\*\s*(\d+)", text)

    role_rows = re.findall(
        r"^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|",
        text,
        re.MULTILINE,
    )
    role_coverage = [
        {"role_category": r.strip(), "count": int(c), "source": s.strip()}
        for r, c, s in role_rows
        if r.strip() not in ("Role Category", "---")
    ]

    return {
        "generated": generated.group(1).strip() if generated else None,
        "total_records": int(total.group(1)) if total else 0,
        "role_coverage": role_coverage,
    }


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
