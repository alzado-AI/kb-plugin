"""kb compliance — CRUD for regulatory compliance tracking."""

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


from ._crud import register_delete

app = typer.Typer(help="Compliance management (regulatory requirements)")


register_delete(app, "compliance", label="compliance item")

@app.command("list")
def list_items(
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    overdue: bool = typer.Option(False, "--overdue", help="Only show past-deadline items"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List compliance items."""
    client = _require_client()
    params = {}
    if estado:
        params["estado"] = estado
    if module:
        params["module"] = module
    if overdue:
        params["overdue"] = "true"
    data = client.list("compliance", **params)

    emit(
        data,
        pretty=pretty,
        columns=["id", "title", "regulation", "deadline", "estado", "responsible", "module"],
        title="Compliance Items",
    )


@app.command("show")
def show_item(
    item_id: int = typer.Argument(..., help="Compliance item ID"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a compliance item by ID."""
    client = _require_client()
    data = client.show("compliance", item_id)

    emit(data, pretty=pretty, title=f"Compliance #{item_id}")


@app.command("create")
def create_item(
    title: str = typer.Argument(..., help="Requirement title"),
    regulation: Optional[str] = typer.Option(None, "--regulation", "-r", help="Regulation name"),
    deadline: Optional[str] = typer.Option(None, "--deadline", "-d", help="Deadline (YYYY-MM-DD)"),
    responsible_email: Optional[str] = typer.Option(None, "--responsible", help="Responsible person email"),
    module_slug: Optional[str] = typer.Option(None, "--module", "-m"),
):
    """Create a new compliance item."""
    client = _require_client()
    payload = dict(title=title)
    if regulation:
        payload["regulation"] = regulation
    if deadline:
        payload["deadline"] = deadline
    if responsible_email:
        payload["responsible"] = responsible_email
    if module_slug:
        payload["module"] = module_slug
    data = client.create("compliance", **payload)

    emit(data)


@app.command("update")
def update_item(
    item_id: int = typer.Argument(..., help="Compliance item ID"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    deadline: Optional[str] = typer.Option(None, "--deadline", "-d"),
    title: Optional[str] = typer.Option(None, "--title"),
):
    """Update a compliance item."""
    client = _require_client()
    updates = {}
    if estado is not None:
        updates["estado"] = estado
    if deadline is not None:
        updates["deadline"] = deadline
    if title is not None:
        updates["title"] = title
    data = client.update("compliance", item_id, **updates)

    emit(data)


@app.command("complete")
def complete_item(
    item_id: int = typer.Argument(..., help="Compliance item ID"),
):
    """Mark a compliance item as fulfilled."""
    client = _require_client()
    data = client.update("compliance", item_id, estado="cumplido")

    emit(data)
