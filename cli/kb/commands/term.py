"""kb term — glossary."""

import json as _json
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Glossary terms")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_terms(
    tipo: Optional[str] = typer.Option(None, "--tipo"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    scope: Optional[str] = typer.Option(None, "--scope"),
    as_of: Optional[str] = typer.Option(None, "--as-of"),
    include_history: bool = typer.Option(False, "--include-history"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    data = client.list(
        "terms",
        tipo=tipo, module=module, scope=scope, as_of=as_of,
        include_history="true" if include_history else None,
    )
    emit(
        data, pretty=pretty,
        columns=["slug", "term", "tipo", "scope", "valid_to"],
        title="Terms",
    )


@app.command("show")
def show(slug: str, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    data = client.show("terms", slug)
    emit(data, pretty=pretty, title=f"Term: {slug}")


@app.command("create")
def create(
    slug: str = typer.Argument(...),
    term: str = typer.Option(..., "--term", "-t"),
    definicion: str = typer.Option("", "--def", "-d"),
    tipo: str = typer.Option("concepto", "--tipo"),
    scope: str = typer.Option("org", "--scope"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    aliases: Optional[str] = typer.Option(
        None, "--aliases", help="Comma-separated",
    ),
    source: str = typer.Option("manual", "--source"),
    confidence: str = typer.Option("confirmed", "--confidence"),
):
    client = _require_client()
    data = client.create(
        "terms",
        slug=slug, term=term, definicion=definicion, tipo=tipo,
        scope=scope, module=module,
        aliases=[a.strip() for a in aliases.split(",")] if aliases else None,
        source=source, confidence=confidence,
    )
    emit(data)


@app.command("update")
def update(
    slug: str = typer.Argument(...),
    term: Optional[str] = typer.Option(None, "--term", "-t"),
    definicion: Optional[str] = typer.Option(None, "--def", "-d"),
    tipo: Optional[str] = typer.Option(None, "--tipo"),
    scope: Optional[str] = typer.Option(None, "--scope"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    aliases: Optional[str] = typer.Option(None, "--aliases"),
):
    client = _require_client()
    payload = {
        k: v for k, v in {
            "term": term, "definicion": definicion, "tipo": tipo,
            "scope": scope, "module": module,
        }.items() if v is not None
    }
    if aliases is not None:
        payload["aliases"] = [a.strip() for a in aliases.split(",")]
    data = client.update("terms", slug, **payload)
    emit(data)


@app.command("resolve")
def resolve(text: str = typer.Argument(...)):
    """Resolve a text snippet to a canonical term (case/accent insensitive)."""
    client = _require_client()
    data = client.post("terms/resolve", data={"text": text})
    emit(data)


@app.command("link")
def link(
    source: str = typer.Argument(...),
    target: str = typer.Argument(...),
    relation: str = typer.Option("related", "--relation"),
):
    client = _require_client()
    data = client.post(
        "terms/link",
        data={"source": source, "target": target, "relation": relation},
    )
    emit(data)


@app.command("delete")
def delete(slug: str):
    client = _require_client()
    emit(client.delete("terms", slug))
