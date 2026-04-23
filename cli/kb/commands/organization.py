"""kb organization — singleton profile of the organization running this instance."""

import json as _json
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Organization profile (singleton)")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("show")
def show(pretty: bool = typer.Option(False, "--pretty", "-p")):
    """Show the organization profile."""
    client = _require_client()
    data = client.get("organization")
    emit(data, pretty=pretty, title="Organization")


@app.command("update")
def update(
    name: Optional[str] = typer.Option(None, "--name"),
    slug: Optional[str] = typer.Option(None, "--slug"),
    industry: Optional[str] = typer.Option(None, "--industry"),
    modelo_negocio: Optional[str] = typer.Option(None, "--modelo-negocio"),
    lineas_negocio: Optional[str] = typer.Option(
        None, "--lineas-negocio", help="JSON array",
    ),
    situaciones_especiales: Optional[str] = typer.Option(
        None, "--situaciones-especiales", help="JSON array",
    ),
):
    """Update the organization profile (admin only)."""
    client = _require_client()
    payload = {}
    if name is not None:
        payload["name"] = name
    if slug is not None:
        payload["slug"] = slug
    if industry is not None:
        payload["industry"] = industry
    if modelo_negocio is not None:
        payload["modelo_negocio"] = modelo_negocio
    if lineas_negocio is not None:
        payload["lineas_negocio"] = _json.loads(lineas_negocio)
    if situaciones_especiales is not None:
        payload["situaciones_especiales"] = _json.loads(situaciones_especiales)
    resp = client._patch("/organization/", json=payload)
    emit(resp.json())


@app.command("coverage")
def coverage(pretty: bool = typer.Option(False, "--pretty", "-p")):
    """Coverage metrics of the org's domain config."""
    client = _require_client()
    data = client.get("organization/coverage")
    emit(data, pretty=pretty, title="Coverage")


@app.command("onboarding")
def onboarding(pretty: bool = typer.Option(False, "--pretty", "-p")):
    """Onboarding progress checklist."""
    client = _require_client()
    data = client.get("organization/onboarding-progress")
    if pretty:
        pct = data.get("percent_complete", 0)
        bar = "█" * (pct // 5) + "░" * (20 - (pct // 5))
        print(f"Onboarding progress: {pct}% [{bar}]")
        print()
        for item in data.get("items", []):
            icon = "[x]" if item["done"] else "[ ]"
            print(f"  {icon} {item['description']}")
        if nxt := data.get("next"):
            print()
            print(f"Siguiente: {nxt}")
    else:
        emit(data)


@app.command("export")
def export_snapshot():
    """Export the org snapshot as JSON to stdout (pipe to file)."""
    client = _require_client()
    data = client.post("organization/export")
    print(_json.dumps(data, indent=2, ensure_ascii=False))


@app.command("import")
def import_snapshot(
    path: str = typer.Argument(..., help="Path to a bundle JSON file"),
    mode: str = typer.Option("merge", "--mode", help="merge | replace"),
    force: bool = typer.Option(False, "--force"),
):
    client = _require_client()
    with open(path) as f:
        bundle = _json.load(f)
    emit(client.post("organization/import", data={
        "bundle": bundle, "mode": mode, "force": force,
    }))


@app.command("diff")
def diff_snapshots(
    from_file: str = typer.Option(..., "--from"),
    to_file: str = typer.Option(..., "--to"),
):
    client = _require_client()
    with open(from_file) as f:
        a = _json.load(f)
    with open(to_file) as f:
        b = _json.load(f)
    result = client.post("organization/diff", data={"from": a, "to": b})
    print(_json.dumps(result, indent=2, ensure_ascii=False))
