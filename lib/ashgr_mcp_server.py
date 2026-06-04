"""
FastMCP server — ahsgr-north-denver corpus.

The filename is retained as ``ashgr_mcp_server.py`` for compatibility with the
current OpenClaw client config.

Tools:
  search_roster      Search officer/board records (docs/roster_index.csv)
  get_chapter_summary  Coverage stats from docs/roster_index.md
  semantic_search    Search the private data-hub-ahsgr LanceDB index
"""

import csv
import os
import re
import sqlite3
from pathlib import Path

from fastmcp import FastMCP

ROOT = Path(__file__).parent.parent
DEFAULT_DATA_HUB = Path("/Volumes/BJH/data-hub-ahsgr")
LANCEDB_TABLE = "ahsgr_denver"
BOARD_INDEX_DB = ROOT / "docs" / "board_index.db"

mcp = FastMCP("ahsgr-north-denver")


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


def _board_db_path() -> Path:
    return Path(os.environ.get("AHSGR_BOARD_INDEX_DB", BOARD_INDEX_DB))


def _query_board_db(sql: str, params: tuple, limit: int, offset: int) -> list[dict]:
    db_path = _board_db_path()
    if not db_path.exists():
        return [{"error": f"board_index.db not found at {db_path}. Run build_board_index.py."}]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in conn.execute(sql, params)]
    finally:
        conn.close()
    return _paginate(rows, limit, offset)


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
    """Search AHSGR Denver officer and board records.

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
    """Return AHSGR Denver roster coverage stats from docs/roster_index.md."""
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
# Tool 3: search_board_documents
# ---------------------------------------------------------------------------

@mcp.tool()
def search_board_documents(
    keyword: str = "",
    doc_type: str = "",
    topic: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Search AHSGR board documents parsed from data-hub-ahsgr."""
    where = []
    params: list[str] = []
    if keyword:
        where.append("(title LIKE ? OR text LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if doc_type:
        where.append("doc_type = ?")
        params.append(doc_type)
    if topic:
        where.append("topic LIKE ?")
        params.append(f"{topic}%")
    if date_from:
        where.append("doc_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("doc_date <= ?")
        params.append(date_to)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return _query_board_db(
        f"""
        SELECT path, title, topic, tier, doc_type, doc_date
        FROM documents
        {clause}
        ORDER BY doc_date DESC, path
        """,
        tuple(params),
        limit,
        offset,
    )


# ---------------------------------------------------------------------------
# Tool 4: search_action_items
# ---------------------------------------------------------------------------

@mcp.tool()
def search_action_items(
    status: str = "open",
    keyword: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Search extracted AHSGR board action items."""
    where = []
    params: list[str] = []
    if status:
        where.append("status = ?")
        params.append(status)
    if keyword:
        where.append("item_text LIKE ?")
        params.append(f"%{keyword}%")
    if date_from:
        where.append("doc_date >= ?")
        params.append(date_from)
    if date_to:
        where.append("doc_date <= ?")
        params.append(date_to)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return _query_board_db(
        f"""
        SELECT document_path, item_text, status, doc_date
        FROM action_items
        {clause}
        ORDER BY doc_date DESC, id
        """,
        tuple(params),
        limit,
        offset,
    )


# ---------------------------------------------------------------------------
# Tool 5: semantic_search
# ---------------------------------------------------------------------------

@mcp.tool()
def semantic_search(
    query: str,
    limit: int = 5,
    topic: str = "",
) -> list[dict]:
    """Semantic search over the private AHSGR data hub.

    Args:
        query: Natural-language search query.
        limit: Max rows to return.
        topic: Optional topic prefix filter, e.g. board/meetings.
    """
    if not query.strip():
        return [{"error": "query is required"}]

    hub = Path(os.environ.get("AHSGR_DATA_HUB_PATH", DEFAULT_DATA_HUB))
    index_dir = hub / "data" / "lancedb"
    if not index_dir.exists():
        return [{"error": f"LanceDB index not found at {index_dir}. Run `make build` in {hub}."}]

    try:
        import lancedb
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        return [{"error": f"Missing semantic search dependency: {exc}"}]

    db = lancedb.connect(str(index_dir))
    if LANCEDB_TABLE not in db.table_names():
        return [{"error": f"Table {LANCEDB_TABLE} not found. Run `make build` in {hub}."}]

    model = SentenceTransformer("all-MiniLM-L6-v2")
    encoded = model.encode(query)
    vector = encoded.tolist() if hasattr(encoded, "tolist") else encoded
    table = db.open_table(LANCEDB_TABLE)
    rows = table.search(vector).limit(max(limit, 1) * 3).to_pandas()
    if topic:
        rows = rows[rows["topic"].str.startswith(topic)]
    rows = rows.head(max(limit, 1))

    results = [
        {
            "path": row.get("path", ""),
            "title": row.get("title", ""),
            "topic": row.get("topic", ""),
            "tier": row.get("tier", ""),
            "year": row.get("year", ""),
            "text": str(row.get("text", ""))[:500],
        }
        for _, row in rows.iterrows()
    ]
    return _paginate(results, limit, 0)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
