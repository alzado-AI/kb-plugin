"""kb drift — drift findings."""

import json as _json
import sys
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Drift findings (provider data anomalies)")


def _require_client():
    client = get_client()
    if not client:
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_findings(
    severity: Optional[str] = typer.Option(None, "--severity"),
    status: Optional[str] = typer.Option(None, "--status"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    data = client.list("drift-findings", severity=severity, status=status)
    emit(
        data, pretty=pretty,
        columns=["id", "scan_at", "entity_type", "severity", "status"],
        title="Drift findings",
    )


@app.command("show")
def show(id: int, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    emit(client.show("drift-findings", id), pretty=pretty)


@app.command("create")
def create(
    description: str = typer.Option(..., "--description"),
    entity_type: str = typer.Option("", "--entity-type"),
    severity: str = typer.Option("info", "--severity"),
    suggested_action: str = typer.Option(
        "{}", "--suggested-action", help="JSON",
    ),
):
    client = _require_client()
    emit(client.create(
        "drift-findings",
        description=description,
        entity_type=entity_type,
        severity=severity,
        suggested_action=_json.loads(suggested_action),
    ))


@app.command("acknowledge")
def acknowledge(id: int = typer.Argument(...)):
    client = _require_client()
    emit(client.post(f"drift-findings/{id}/acknowledge"))
