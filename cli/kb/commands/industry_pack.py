"""kb industry-pack — reusable domain bundles per vertical."""

import json as _json
import sys
from typing import Optional

import typer

from ..client import get_client
from ..output import emit
from ._crud import register_update

app = typer.Typer(help="Industry packs (reusable domain bundles)")

register_update(app, "industry-packs", label="industry pack")


def _require_client():
    client = get_client()
    if not client:
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_packs(pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    data = client.list("industry-packs")
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "country", "industry", "items_count"],
        title="Industry packs",
    )


@app.command("show")
def show(slug: str, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    emit(client.show("industry-packs", slug), pretty=pretty)


@app.command("create")
def create_pack(
    slug: str = typer.Argument(..., help="Unique slug"),
    name: str = typer.Option(..., "--name", "-n"),
    country: Optional[str] = typer.Option(None, "--country"),
    industry: Optional[str] = typer.Option(None, "--industry"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
):
    """Create a new industry pack."""
    client = _require_client()
    data = client.create(
        "industry-packs",
        slug=slug, name=name, country=country,
        industry=industry, description=description,
    )
    emit(data)


@app.command("apply")
def apply(
    slug: str = typer.Argument(...),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    client = _require_client()
    emit(client.post(
        f"industry-packs/{slug}/apply",
        data={"dry_run": dry_run},
    ))


@app.command("create-from-current")
def create_from_current(
    slug: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None, "--name"),
    country: str = typer.Option("", "--country"),
    industry: str = typer.Option("", "--industry"),
    descripcion: str = typer.Option("", "--descripcion"),
):
    client = _require_client()
    emit(client.post(
        "industry-packs/create-from-current",
        data={
            "slug": slug, "name": name or slug,
            "country": country, "industry": industry,
            "descripcion": descripcion,
        },
    ))


@app.command("export")
def export(slug: str = typer.Argument(...)):
    """Print the pack as JSON to stdout (pipe to a file)."""
    client = _require_client()
    data = client.get(f"industry-packs/{slug}/export")
    print(_json.dumps(data, indent=2, ensure_ascii=False))


@app.command("import")
def import_pack(
    path: str = typer.Argument(..., help="Path to a bundle JSON file"),
):
    client = _require_client()
    with open(path) as f:
        bundle = _json.load(f)
    emit(client.post("industry-packs/import", data=bundle))


@app.command("delete")
def delete(slug: str):
    client = _require_client()
    emit(client.delete("industry-packs", slug))
