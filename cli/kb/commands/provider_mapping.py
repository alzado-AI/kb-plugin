"""kb provider-mapping — semantic mappings over provider data."""

import json as _json
from typing import List, Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Provider semantic mappings")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_mappings(
    provider: Optional[str] = typer.Option(None, "--provider"),
    entity_type: Optional[str] = typer.Option(None, "--entity-type"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    data = client.list("provider-mappings", provider=provider, entity_type=entity_type)
    emit(
        data, pretty=pretty,
        columns=["id", "provider", "entity_type", "tags", "rules"],
        title="Provider mappings",
    )


@app.command("show")
def show(id: int, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    emit(client.show("provider-mappings", id), pretty=pretty)


@app.command("create")
def create(
    provider: str = typer.Option(..., "--provider", help="Provider slug (e.g. odoo, hubspot)"),
    entity_type: str = typer.Option(..., "--entity-type"),
    selector: str = typer.Option("{}", "--selector", help="JSON object"),
    tag: List[str] = typer.Option(
        [], "--tag", help="Term slug to attach (repeatable)",
    ),
    rule: List[str] = typer.Option(
        [], "--rule", help="BusinessRule slug to attach (repeatable)",
    ),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    client = _require_client()
    emit(client.create(
        "provider-mappings",
        provider=provider,
        entity_type=entity_type,
        selector=_json.loads(selector),
        tag_slugs=list(tag) or None,
        rule_slugs=list(rule) or None,
        notes=notes,
    ))


@app.command("update")
def update(
    id: int,
    entity_type: Optional[str] = typer.Option(None, "--entity-type"),
    selector: Optional[str] = typer.Option(None, "--selector"),
    tag: List[str] = typer.Option([], "--tag"),
    rule: List[str] = typer.Option([], "--rule"),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    client = _require_client()
    payload = {}
    if entity_type is not None:
        payload["entity_type"] = entity_type
    if selector is not None:
        payload["selector"] = _json.loads(selector)
    if tag:
        payload["tag_slugs"] = list(tag)
    if rule:
        payload["rule_slugs"] = list(rule)
    if notes is not None:
        payload["notes"] = notes
    emit(client.update("provider-mappings", id, **payload))


@app.command("delete")
def delete(id: int):
    client = _require_client()
    emit(client.delete("provider-mappings", id))
