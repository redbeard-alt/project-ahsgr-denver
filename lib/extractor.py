"""Extract name/role records from AHSGR newsletter markdown or PDF text."""

import re
from pathlib import Path

from .normalizer import make_record

# Patterns for officer/board blocks in newsletter text.
# Extend as source format becomes clearer.
_OFFICER_LINE = re.compile(
    r"(?P<role>President|Vice[\s-]?President|Secretary|Treasurer|Director|"
    r"Newsletter\s+Editor|Marketing\s+Director|Member\s+Committee\s+Chair(?:man)?|"
    r"Webmaster)[:\s]+(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
    re.IGNORECASE,
)


def extract_from_text(
    text: str,
    source_file: str = "",
    start_date: str = "",
    end_date: str = "",
) -> list[dict]:
    records = []
    for m in _OFFICER_LINE.finditer(text):
        records.append(
            make_record(
                name=m.group("name"),
                role=m.group("role"),
                start_date=start_date,
                end_date=end_date,
                source_file=source_file,
            )
        )
    return records


def extract_from_file(path: Path, start_date: str = "", end_date: str = "") -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        except Exception as e:
            print(f"  WARNING: pdfplumber failed on {path.name}: {e}")
            return []
    else:
        text = path.read_text(encoding="utf-8", errors="replace")

    return extract_from_text(text, source_file=path.name, start_date=start_date, end_date=end_date)
