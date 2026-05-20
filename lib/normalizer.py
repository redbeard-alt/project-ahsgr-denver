"""Normalize extracted name/role records to the roster_index schema."""

import re
from pathlib import Path

import yaml

_RULES = yaml.safe_load((Path(__file__).parent.parent / "config" / "format_rules.yml").read_text())
_ALL_ROLES = {r for cat in _RULES["roles"].values() for r in cat}


def normalize_name(raw: str) -> str:
    """Coerce 'First Last' or 'Last, First' to 'Last, First'."""
    raw = raw.strip()
    if "," in raw:
        return raw
    parts = raw.split()
    if len(parts) >= 2:
        return f"{parts[-1]}, {' '.join(parts[:-1])}"
    return raw


def normalize_role(raw: str) -> str:
    """Lowercase + underscore a role string; return as-is if unrecognized."""
    slug = re.sub(r"[\s\-/]+", "_", raw.strip().lower())
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    return slug if slug in _ALL_ROLES else slug


def role_category(role: str) -> str:
    for cat, roles in _RULES["roles"].items():
        if role in roles:
            return cat
    return "unknown"


def make_record(
    name: str,
    role: str,
    start_date: str = "",
    end_date: str = "",
    source_file: str = "",
    source_page: str = "",
    notes: str = "",
) -> dict:
    n = normalize_name(name)
    r = normalize_role(role)
    return {
        "name": n,
        "role": r,
        "role_category": role_category(r),
        "start_date": start_date,
        "end_date": end_date,
        "source_file": source_file,
        "source_page": source_page,
        "notes": notes,
    }
