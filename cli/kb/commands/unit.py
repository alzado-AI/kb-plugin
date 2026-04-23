"""kb unit — units + conversions."""

import json as _json
from decimal import Decimal
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

from ._crud import register_delete, register_update

app = typer.Typer(help="Units and conversions")


register_delete(app, "units", label="unit")
register_update(app, "units", label="unit")

def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_units(
    dimension: Optional[str] = typer.Option(None, "--dimension"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    data = client.list("units", dimension=dimension)
    emit(
        data, pretty=pretty,
        columns=["code", "name", "symbol", "dimension", "is_base"],
        title="Units",
    )


@app.command("create")
def create(
    code: str = typer.Argument(...),
    name: str = typer.Option(..., "--name"),
    symbol: str = typer.Option("", "--symbol"),
    dimension: str = typer.Option("custom", "--dimension"),
    is_base: bool = typer.Option(False, "--is-base"),
):
    client = _require_client()
    emit(client.create(
        "units", code=code, name=name, symbol=symbol,
        dimension=dimension, is_base=is_base,
    ))


@app.command("convert")
def convert_value(
    value: str = typer.Argument(...),
    from_code: str = typer.Argument(..., metavar="FROM"),
    to_code: str = typer.Argument(..., metavar="TO"),
    context: Optional[str] = typer.Option(None, "--context", help="JSON"),
):
    """Call /units/convert/ endpoint on the backend."""
    client = _require_client()
    payload = {"value": value, "from": from_code, "to": to_code}
    if context:
        payload["context"] = _json.loads(context)
    emit(client.post("units/convert", data=payload))


@app.command("add-conversion")
def add_conversion(
    from_code: str = typer.Argument(...),
    to_code: str = typer.Argument(...),
    factor: str = typer.Option(..., "--factor"),
    context: Optional[str] = typer.Option(None, "--context"),
    notes: Optional[str] = typer.Option(None, "--notes"),
):
    client = _require_client()
    payload = {
        "from_code": from_code, "to_code": to_code, "factor": factor,
    }
    if context:
        payload["context"] = _json.loads(context)
    if notes:
        payload["notes"] = notes
    emit(client.post("units/add-conversion", data=payload))
