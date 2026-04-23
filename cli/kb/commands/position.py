"""kb position — roles estructurales de la organizacion."""

import json as _json
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Positions (roles estructurales)")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_positions(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    data = client.list("positions", module=module)
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "module", "reports_to"],
        title="Positions",
    )


@app.command("show")
def show(slug: str, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    emit(client.show("positions", slug), pretty=pretty, title=f"Position: {slug}")


@app.command("create")
def create(
    slug: str = typer.Argument(...),
    name: str = typer.Option(..., "--name"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    reports_to: Optional[str] = typer.Option(None, "--reports-to"),
    responsabilidades: Optional[str] = typer.Option(
        None, "--responsabilidades", help="Comma-separated list",
    ),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    client = _require_client()
    payload = {"slug": slug, "name": name, "module": module, "reports_to": reports_to}
    if responsabilidades:
        payload["responsabilidades"] = [
            r.strip() for r in responsabilidades.split(",")
        ]
    if notes is not None:
        payload["notes"] = notes
    emit(client.create("positions", **payload))


@app.command("update")
def update(
    slug: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None, "--name"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    reports_to: Optional[str] = typer.Option(None, "--reports-to"),
    responsabilidades: Optional[str] = typer.Option(None, "--responsabilidades"),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    client = _require_client()
    payload = {}
    if name is not None:
        payload["name"] = name
    if module is not None:
        payload["module"] = module
    if reports_to is not None:
        payload["reports_to"] = reports_to
    if responsabilidades is not None:
        payload["responsabilidades"] = [
            r.strip() for r in responsabilidades.split(",")
        ]
    if notes is not None:
        payload["notes"] = notes
    emit(client.update("positions", slug, **payload))


@app.command("delete")
def delete(slug: str):
    client = _require_client()
    emit(client.delete("positions", slug))
