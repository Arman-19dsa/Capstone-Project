"""
csv_import.py
Parses an uploaded CSV (bank/UPI statement export or manual export)
into a normalized list of row dicts the Orchestrator can process.
"""

import csv
import io

COLUMN_ALIASES = {
    "date": ["date", "transaction date", "txn date", "value date"],
    "description": ["description", "narration", "particulars", "details", "remarks"],
    "amount": ["amount", "debit", "withdrawal amt", "withdrawal amt.", "amount (inr)", "amt"],
    "category": ["category"],
}


def _normalize_header(header: str) -> str:
    return header.strip().lower()


def _map_columns(fieldnames: list) -> dict:
    normalized = {_normalize_header(f): f for f in fieldnames}
    mapping = {}
    for internal_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[internal_name] = normalized[alias]
                break
    return mapping


def parse_csv_bytes(file_bytes: bytes) -> list:
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        return []

    column_map = _map_columns(reader.fieldnames)
    rows = []

    for raw_row in reader:
        row = {}
        for internal_name, actual_col in column_map.items():
            row[internal_name] = raw_row.get(actual_col, "")
        rows.append(row)

    return rows