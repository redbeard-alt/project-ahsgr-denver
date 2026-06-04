"""Tests for ashgr_mcp_server tools (offline — no gateway required)."""

import csv
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.ashgr_mcp_server import search_roster, get_chapter_summary, semantic_search
from lib.normalizer import normalize_name, normalize_role, role_category, make_record


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------

class TestNormalizer:
    def test_normalize_name_already_last_first(self):
        assert normalize_name("Smith, John") == "Smith, John"

    def test_normalize_name_first_last(self):
        assert normalize_name("John Smith") == "Smith, John"

    def test_normalize_role_newsletter_editor(self):
        assert normalize_role("Newsletter Editor") == "newsletter_editor"

    def test_normalize_role_member_committee_chair(self):
        result = normalize_role("Member Committee Chairman")
        assert "member_committee_chair" in result

    def test_role_category_board(self):
        assert role_category("president") == "board"

    def test_role_category_officer(self):
        assert role_category("newsletter_editor") == "officers"

    def test_make_record_shape(self):
        r = make_record("Jane Doe", "president", start_date="2024-01-01")
        assert set(r.keys()) == {"name", "role", "role_category", "start_date", "end_date",
                                  "source_file", "source_page", "notes"}


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

class TestMCPTools:
    def test_search_roster_returns_meta(self):
        result = search_roster()
        assert result[-1].get("_meta") is True

    def test_search_roster_total_is_nonnegative(self):
        result = search_roster()
        assert result[-1]["_total"] >= 0

    def test_search_roster_filters_by_role(self):
        result = search_roster(role="president")
        hits = [r for r in result if not r.get("_meta")]
        assert all("president" in r["role"] for r in hits)

    def test_get_chapter_summary_no_error_when_md_exists(self, tmp_path, monkeypatch):
        import lib.ashgr_mcp_server as srv
        monkeypatch.setattr(srv, "ROOT", tmp_path)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "roster_index.md").write_text(
            "**Generated:** 2026-01-01\n**Total records:** 5\n"
        )
        result = srv.get_chapter_summary()
        assert result["total_records"] == 5

    def test_get_chapter_summary_missing_md(self, tmp_path, monkeypatch):
        import lib.ashgr_mcp_server as srv
        monkeypatch.setattr(srv, "ROOT", tmp_path)
        (tmp_path / "docs").mkdir()
        result = srv.get_chapter_summary()
        assert "error" in result

    def test_semantic_search_reports_missing_index(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AHSGR_DATA_HUB_PATH", str(tmp_path))
        result = semantic_search("maifest")
        assert "LanceDB index not found" in result[0]["error"]

    def test_semantic_search_returns_rows(self, tmp_path, monkeypatch):
        hub = tmp_path / "hub"
        (hub / "data" / "lancedb").mkdir(parents=True)
        monkeypatch.setenv("AHSGR_DATA_HUB_PATH", str(hub))

        class _Rows:
            def __init__(self, rows):
                self.rows = rows

            def __getitem__(self, _mask):
                return self

            def head(self, n):
                return _Rows(self.rows[:n])

            def iterrows(self):
                return iter(enumerate(self.rows))

        class _StrAccessor:
            def startswith(self, _topic):
                return [True]

        class _TopicColumn:
            str = _StrAccessor()

        class _Frame(_Rows):
            def __getitem__(self, key):
                if key == "topic":
                    return _TopicColumn()
                return super().__getitem__(key)

        class _Search:
            def limit(self, _limit):
                return self

            def to_pandas(self):
                return _Frame([
                    {
                        "path": "board/meetings/example.md",
                        "title": "Example Meeting",
                        "topic": "board/meetings",
                        "tier": "private",
                        "year": "2026",
                        "text": "Meeting action items",
                    }
                ])

        class _Table:
            def search(self, _vector):
                return _Search()

        class _Db:
            def table_names(self):
                return ["ahsgr_denver"]

            def open_table(self, _name):
                return _Table()

        class _Model:
            def __init__(self, _name):
                pass

            def encode(self, _query):
                return [0.1, 0.2]

        monkeypatch.setitem(sys.modules, "lancedb", types.SimpleNamespace(connect=lambda _path: _Db()))
        monkeypatch.setitem(
            sys.modules,
            "sentence_transformers",
            types.SimpleNamespace(SentenceTransformer=_Model),
        )

        result = semantic_search("meeting", topic="board/meetings")
        hits = [row for row in result if not row.get("_meta")]
        assert hits[0]["title"] == "Example Meeting"
        assert result[-1]["_total"] == 1
