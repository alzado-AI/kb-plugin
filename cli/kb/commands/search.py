"""kb search — Cross-entity full-text search."""

import sys
from typing import Optional

import typer

from ..client import get_client
from ..output import emit


# Mirror of backend/apps/core/search.py VALID_TYPES. Kept in sync manually
# so the CLI can give a friendly warning without an extra API round trip.
VALID_TYPES = (
    "account_plan", "agent", "budget", "cashflow_item", "client_feedback",
    "command", "company", "compliance_item", "content", "contract",
    "conversation", "decision", "document", "interaction", "invoice", "issue",
    "learning", "meeting", "module", "need", "objective", "opportunity",
    "person", "process", "product", "program", "project", "question",
    "report", "rule", "sales_goal", "script", "skill",
    "team", "template", "term", "todo",
)


def _require_client():
    client = get_client()
    if not client:
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


def search(
    keyword: str = typer.Argument(..., help="Search keyword"),
    type: Optional[str] = typer.Option(
        None, "--type", "-t",
        help=f"Comma-separated entity types. Valid: {', '.join(VALID_TYPES)}",
    ),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results per type"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """Search across all KB entities using full-text search."""
    types = [t.strip() for t in type.split(",")] if type else None
    if types:
        unknown = [t for t in types if t not in VALID_TYPES]
        if unknown:
            print(
                f"warning: unknown --type value(s): {', '.join(unknown)}. "
                f"Valid types: {', '.join(VALID_TYPES)}",
                file=sys.stderr,
            )

    client = _require_client()
    results = client.search(
        keyword,
        type=",".join(types) if types else None,
        limit=limit,
    )
    data = {
        "query": keyword,
        "total": len(results),
        "results": results,
    }

    if not pretty:
        emit(data)
    else:
        from rich.console import Console
        from rich.table import Table

        console = Console()

        if not results:
            console.print(f"[dim]No results for '{keyword}'[/dim]")
            return

        # Group by type
        grouped: dict[str, list] = {}
        for r in results:
            grouped.setdefault(r["type"], []).append(r)

        for type_name, items in grouped.items():
            table = Table(title=f"{type_name.upper()} ({len(items)})", show_lines=False)
            table.add_column("ID", style="dim", width=6)
            table.add_column("Title")
            table.add_column("Rank", width=8)
            table.add_column("Context", style="dim")
            for item in items:
                ctx = ", ".join(f"{k}={v}" for k, v in (item.get("context") or {}).items() if v)
                table.add_row(
                    str(item["id"]),
                    item["title"][:80],
                    f"{item.get('rank', 0):.4f}",
                    ctx[:60],
                )
            console.print(table)
            console.print()
