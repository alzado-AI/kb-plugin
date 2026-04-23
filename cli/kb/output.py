"""Output formatting: JSON (default for agents) and Rich tables (--pretty)."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def emit_json(data: Any):
    """Print JSON to stdout (default mode for agent consumption)."""
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False, default=str)
    print()


def emit_table(columns: list[str], rows: list[list[Any]], title: str = ""):
    """Print a Rich table for human consumption (--pretty mode)."""
    table = Table(title=title, show_lines=False)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(v) if v is not None else "" for v in row])
    console.print(table)


def extract_field(data: Any, field_path: str) -> Any:
    """Extract a nested field from a dict using dot-notation path (e.g. 'content.propuesta.id')."""
    parts = field_path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def emit(data: Any, pretty: bool = False, columns: list[str] | None = None, title: str = ""):
    """Unified output: JSON by default, Rich table if --pretty."""
    if not pretty:
        emit_json(data)
        return

    if isinstance(data, list) and columns:
        rows = []
        for item in data:
            row = [item.get(c, "") if isinstance(item, dict) else getattr(item, c, "") for c in columns]
            rows.append(row)
        emit_table(columns, rows, title=title)
    elif isinstance(data, dict):
        # Single record: key-value display
        table = Table(title=title, show_lines=True)
        table.add_column("Field")
        table.add_column("Value")
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v, indent=2, ensure_ascii=False, default=str)
            table.add_row(str(k), str(v) if v is not None else "")
        console.print(table)
    else:
        emit_json(data)
