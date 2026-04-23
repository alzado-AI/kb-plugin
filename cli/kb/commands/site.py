"""kb site — physical sites (plantas, acopios, oficinas)."""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Sites (lugares fisicos)")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_sites(pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    data = client.list("sites")
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "tipo", "city", "legal_entity"],
        title="Sites",
    )


@app.command("show")
def show(slug: str, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    emit(client.show("sites", slug), pretty=pretty)


@app.command("create")
def create(
    slug: str = typer.Argument(...),
    name: str = typer.Option(..., "--name"),
    tipo: str = typer.Option("custom", "--tipo"),
    city: Optional[str] = typer.Option(None, "--city"),
    country: Optional[str] = typer.Option(None, "--country"),
    address: Optional[str] = typer.Option(None, "--address"),
    legal_entity: Optional[str] = typer.Option(None, "--legal-entity"),
):
    client = _require_client()
    emit(client.create(
        "sites", slug=slug, name=name, tipo=tipo,
        city=city, country=country, address=address,
        legal_entity=legal_entity,
    ))


@app.command("update")
def update(
    slug: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None, "--name"),
    tipo: Optional[str] = typer.Option(None, "--tipo"),
    city: Optional[str] = typer.Option(None, "--city"),
    legal_entity: Optional[str] = typer.Option(None, "--legal-entity"),
):
    client = _require_client()
    payload = {
        k: v for k, v in {
            "name": name, "tipo": tipo, "city": city,
            "legal_entity": legal_entity,
        }.items() if v is not None
    }
    emit(client.update("sites", slug, **payload))


@app.command("delete")
def delete(slug: str):
    client = _require_client()
    emit(client.delete("sites", slug))
