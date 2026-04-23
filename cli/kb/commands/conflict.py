"""kb conflict — pending contradictions resolution."""

import sys
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Conflicts (pending value contradictions)")


def _require_client():
    client = get_client()
    if not client:
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_conflicts(
    pending: bool = typer.Option(False, "--pending"),
    entity_type: Optional[str] = typer.Option(None, "--entity-type"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    params = {"entity_type": entity_type}
    if pending:
        params["status"] = "pending"
    data = client.list("conflicts", **params)
    emit(
        data, pretty=pretty,
        columns=["id", "entity_type", "entity_id", "field", "status"],
        title="Conflicts",
    )


@app.command("show")
def show(id: int, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    emit(client.show("conflicts", id), pretty=pretty)


@app.command("resolve")
def resolve(
    id: int = typer.Argument(...),
    keep: str = typer.Option(
        ..., "--keep", help="current | proposed | merge | ignore",
    ),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    client = _require_client()
    emit(client.post(
        f"conflicts/{id}/resolve",
        data={"decision": keep, "notes": notes or ""},
    ))
