"""Build docs/board_index.db from the private AHSGR data hub board corpus."""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
DEFAULT_HUB = Path("/Volumes/BJH/data-hub-ahsgr")
DB_PATH = ROOT / "docs" / "board_index.db"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, parts[2].lstrip("\n")


def _doc_type(path: Path, body: str) -> str:
    name = path.name.lower()
    if "action-item" in name:
        return "action_items"
    if "minutes" in name:
        return "minutes"
    if "transcript" in name:
        return "transcript"
    if "correspondence" in path.parts:
        return "correspondence"
    if re.search(r"^##\s+transcript\b", body, re.MULTILINE | re.IGNORECASE):
        return "transcript"
    return "note"


def _doc_date(path: Path, meta: dict) -> str:
    value = str(meta.get("date") or "")
    if value:
        return value[:10]
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", path.name)
    return match.group(1) if match else ""


def _extract_action_items(body: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    in_action_section = False
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        bold_action = re.match(r"^\*\*Action items?:\*\*\s*(.*)$", line, re.IGNORECASE)
        if bold_action:
            in_action_section = True
            item = bold_action.group(1).strip()
            if item:
                out.append(("open", item))
            continue
        header = re.match(r"^#{1,4}\s+(.+)$", line)
        if header:
            in_action_section = "action" in header.group(1).lower()
            continue
        table = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$", line)
        if table:
            action = table.group(2).strip()
            owner = table.group(3).strip()
            target = table.group(4).strip()
            out.append(("open", f"{action} — owner: {owner}; target: {target}"))
            continue
        checkbox = re.match(r"^[-*]\s+\[( |x|X)\]\s+(.+)$", line)
        if checkbox:
            status = "closed" if checkbox.group(1).lower() == "x" else "open"
            out.append((status, checkbox.group(2).strip()))
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        if in_action_section and bullet:
            out.append(("open", bullet.group(1).strip()))
    return out


def build_index(hub: Path | None = None, db_path: Path = DB_PATH) -> int:
    hub = hub or Path(os.environ.get("AHSGR_DATA_HUB_PATH", DEFAULT_HUB))
    board_dir = hub / "board"
    if not board_dir.exists():
        raise FileNotFoundError(f"AHSGR board corpus not found: {board_dir}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            topic TEXT NOT NULL,
            tier TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            doc_date TEXT,
            text TEXT NOT NULL
        );

        CREATE TABLE action_items (
            id INTEGER PRIMARY KEY,
            document_path TEXT NOT NULL,
            item_text TEXT NOT NULL,
            status TEXT NOT NULL,
            doc_date TEXT,
            FOREIGN KEY(document_path) REFERENCES documents(path)
        );

        CREATE INDEX idx_documents_type_date ON documents(doc_type, doc_date);
        CREATE INDEX idx_action_items_status_date ON action_items(status, doc_date);
        """
    )

    count = 0
    for md in sorted(board_dir.rglob("*.md")):
        rel = md.relative_to(hub)
        text = md.read_text(encoding="utf-8", errors="replace")
        meta, body = _parse_frontmatter(text)
        title = str(meta.get("title") or md.stem.replace("-", " ").title())
        topic = str(meta.get("topic") or "/".join(rel.parts[:2]))
        tier = str(meta.get("tier") or "private")
        doc_type = _doc_type(rel, body)
        doc_date = _doc_date(rel, meta)
        conn.execute(
            """
            INSERT INTO documents(path, title, topic, tier, doc_type, doc_date, text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(rel), title, topic, tier, doc_type, doc_date, body.strip()),
        )
        for status, item_text in _extract_action_items(body):
            conn.execute(
                """
                INSERT INTO action_items(document_path, item_text, status, doc_date)
                VALUES (?, ?, ?, ?)
                """,
                (str(rel), item_text, status, doc_date),
            )
        count += 1

    conn.commit()
    conn.close()
    return count


if __name__ == "__main__":
    total = build_index()
    print(f"indexed {total} board documents -> {DB_PATH}")
