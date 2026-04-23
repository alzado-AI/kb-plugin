"""kb legal-entity — sociedades del grupo."""

import json as _json
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Legal entities (sociedades del grupo)")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_entities(pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    data = client.list("legal-entities")
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "tax_id", "country", "is_default"],
        title="Legal entities",
    )


@app.command("show")
def show(slug: str, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    data = client.show("legal-entities", slug)
    emit(data, pretty=pretty, title=f"LegalEntity: {slug}")


@app.command("create")
def create(
    slug: str = typer.Argument(...),
    name: str = typer.Option(..., "--name"),
    tax_id: Optional[str] = typer.Option(None, "--tax-id"),
    country: Optional[str] = typer.Option(None, "--country"),
    is_default: bool = typer.Option(False, "--is-default"),
    purposes: Optional[str] = typer.Option(
        None, "--purposes", help="JSON array of strings",
    ),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    client = _require_client()
    data = client.create(
        "legal-entities",
        slug=slug, name=name, tax_id=tax_id, country=country,
        is_default=is_default,
        purposes=_json.loads(purposes) if purposes else None,
        notes=notes,
    )
    emit(data)


@app.command("update")
def update(
    slug: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None, "--name"),
    tax_id: Optional[str] = typer.Option(None, "--tax-id"),
    country: Optional[str] = typer.Option(None, "--country"),
    is_default: Optional[bool] = typer.Option(None, "--is-default"),
    purposes: Optional[str] = typer.Option(None, "--purposes"),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    client = _require_client()
    payload = {
        k: v for k, v in {
            "name": name, "tax_id": tax_id, "country": country,
            "is_default": is_default, "notes": notes,
        }.items() if v is not None
    }
    if purposes is not None:
        payload["purposes"] = _json.loads(purposes)
    data = client.update("legal-entities", slug, **payload)
    emit(data)


@app.command("delete")
def delete(slug: str):
    client = _require_client()
    emit(client.delete("legal-entities", slug))
