"""kb zone — conceptual zones (Norte, Centro, Sur)."""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Zones (agrupaciones comerciales/operativas)")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_zones(pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    data = client.list("zones")
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "descripcion"],
        title="Zones",
    )


@app.command("show")
def show(slug: str, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    emit(client.show("zones", slug), pretty=pretty)


@app.command("create")
def create(
    slug: str = typer.Argument(...),
    name: str = typer.Option(..., "--name"),
    descripcion: Optional[str] = typer.Option(None, "--descripcion", "-d"),
):
    client = _require_client()
    emit(client.create("zones", slug=slug, name=name, descripcion=descripcion))


@app.command("add-site")
def add_site(
    zone_slug: str = typer.Argument(...),
    site_slug: str = typer.Argument(...),
    primary: bool = typer.Option(False, "--primary"),
):
    client = _require_client()
    emit(client.post(
        f"zones/{zone_slug}/add-site",
        data={"site": site_slug, "is_primary": primary},
    ))


@app.command("delete")
def delete(slug: str):
    client = _require_client()
    emit(client.delete("zones", slug))
