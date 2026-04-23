"""kb rule — business rules with versioning + resolution by specificity."""

import json as _json
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Business rules")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_rules(
    scope: Optional[str] = typer.Option(None, "--scope"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    as_of: Optional[str] = typer.Option(None, "--as-of"),
    include_history: bool = typer.Option(False, "--include-history"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    data = client.list(
        "business-rules",
        scope=scope, module=module, as_of=as_of,
        include_history="true" if include_history else None,
    )
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "scope", "priority", "valid_to"],
        title="Business rules",
    )


@app.command("show")
def show(slug: str, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    data = client.show("business-rules", slug)
    emit(data, pretty=pretty, title=f"Rule: {slug}")


@app.command("create")
def create(
    slug: str = typer.Argument(...),
    name: str = typer.Option(..., "--name"),
    contexto: str = typer.Option("{}", "--contexto", help="JSON object"),
    condicion: str = typer.Option("", "--condicion"),
    accion: str = typer.Option("", "--accion"),
    rationale: str = typer.Option("", "--rationale"),
    scope: str = typer.Option("org", "--scope"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    priority: int = typer.Option(0, "--priority"),
):
    client = _require_client()
    data = client.create(
        "business-rules",
        slug=slug, name=name,
        contexto=_json.loads(contexto),
        condicion=condicion, accion=accion, rationale=rationale,
        scope=scope, module=module, priority=priority,
    )
    emit(data)


@app.command("update")
def update(
    slug: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None, "--name"),
    contexto: Optional[str] = typer.Option(None, "--contexto"),
    condicion: Optional[str] = typer.Option(None, "--condicion"),
    accion: Optional[str] = typer.Option(None, "--accion"),
    rationale: Optional[str] = typer.Option(None, "--rationale"),
    scope: Optional[str] = typer.Option(None, "--scope"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    priority: Optional[int] = typer.Option(None, "--priority"),
):
    client = _require_client()
    payload = {
        k: v for k, v in {
            "name": name, "condicion": condicion, "accion": accion,
            "rationale": rationale, "scope": scope, "module": module,
            "priority": priority,
        }.items() if v is not None
    }
    if contexto is not None:
        payload["contexto"] = _json.loads(contexto)
    data = client.update("business-rules", slug, **payload)
    emit(data)


@app.command("resolve")
def resolve(
    contexto: str = typer.Option(..., "--contexto", help="JSON object"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
):
    """Return rules matching the given contexto, most specific first."""
    client = _require_client()
    data = client.post(
        "business-rules/resolve",
        data={"contexto": _json.loads(contexto), "module": module},
    )
    emit(data)


@app.command("delete")
def delete(slug: str):
    client = _require_client()
    emit(client.delete("business-rules", slug))
