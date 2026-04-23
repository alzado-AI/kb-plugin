"""kb entity-state -- query valid states/types for entities."""

import json
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Query valid entity states and types.")


@app.command("list")
def list_states(
    entity: Optional[str] = typer.Option(None, "--entity", "-e", help="Entity type (program, project, issue, opportunity, etc.)"),
    field: Optional[str] = typer.Option(None, "--field", "-f", help="Field name (estado, stage, tipo, priority, escala)"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List valid state/type values for entities.

    Examples:
        kb entity-state list
        kb entity-state list --entity program --field estado
        kb entity-state list --entity opportunity --field stage
    """
    client = get_client()
    if not client:
        raise typer.Exit(1)

    params = {}
    if entity:
        params["entity_type"] = entity
    if field:
        params["field_name"] = field

    data = client.get("entity-states", **params)
    emit(data, pretty=pretty)
