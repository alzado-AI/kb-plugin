"""kb context — Key-value store for context (replaces general.md, metodologia.md)."""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


app = typer.Typer(help="Context key-value store (general, metodologia, etc.)")


@app.command("list")
def list_context(
    section: Optional[str] = typer.Option(None, "--section", "-s"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List all context entries, optionally filtered by section."""
    client = _require_client()
    data = client.list("context", section=section)

    emit(
        data,
        pretty=pretty,
        columns=["id", "section", "key", "value"],
        title="Context",
    )


@app.command("show")
def show_context(
    key: str = typer.Argument(..., help="Context key"),
    section: str = typer.Option("general", "--section", "-s"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a context entry by key and section."""
    client = _require_client()
    data = client.show("context", key, section=section)

    emit(data, pretty=pretty, title=f"Context: {section}/{key}")


@app.command("set")
def set_context(
    key: str = typer.Argument(..., help="Context key"),
    value: str = typer.Argument(..., help="Context value"),
    section: str = typer.Option("general", "--section", "-s"),
):
    """Set a context key-value pair (upsert)."""
    client = _require_client()
    data = client.create("context", section=section, key=key, value=value)

    emit(data)


@app.command("delete")
def delete_context(
    key: str = typer.Argument(..., help="Context key"),
    section: str = typer.Option("general", "--section", "-s"),
):
    """Delete a context entry."""
    client = _require_client()
    data = client.delete("context", key, section=section)

    emit(data)


@app.command("ancestry")
def ancestry(
    entity_type: str = typer.Argument(..., help="Entity type (issue, project, program)"),
    entity_id: int = typer.Argument(..., help="Entity ID"),
    pretty: bool = typer.Option(True, "--pretty/--no-pretty"),
):
    """Walk entity hierarchy upward: entity → project → program → needs → objectives.

    Returns the full context ancestry chain including content snippets
    and active blockers at each level. Agents should call this before
    acting on any entity for strategic alignment.
    """
    client = _require_client()
    data = client.get(f"ancestry/{entity_type}/{entity_id}")
    emit(data, pretty=pretty, title=f"Ancestry: {entity_type}/{entity_id}")
