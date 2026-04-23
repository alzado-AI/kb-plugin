"""kb dashboard — CRUD + card management + render for BI dashboards."""

from typing import Optional

import typer

from ..output import emit
from ._crud import _client_or_die as _require_client, _parse_json

app = typer.Typer(help="Dashboard management (BI)")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@app.command("list")
def list_dashboards(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List dashboards."""
    client = _require_client()
    data = client.list("dashboards", module=module)
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "module", "card_count", "updated_at"],
        title="Dashboards",
    )


@app.command("show")
def show_dashboard(
    slug: str = typer.Argument(...),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a dashboard (with cards)."""
    client = _require_client()
    data = client.show("dashboards", slug)
    emit(data, pretty=pretty, title=f"Dashboard: {slug}")


@app.command("create")
def create_dashboard(
    slug: str = typer.Argument(..., help="Dashboard slug (kebab-case)"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    description: str = typer.Option("", "--description", "-d"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    parameters: Optional[str] = typer.Option(
        None, "--parameters",
        help='JSON list of parameter definitions: [{"name","widget",...}]',
    ),
    layout: Optional[str] = typer.Option(None, "--layout", help="Grid JSON"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
):
    """Create a dashboard."""
    client = _require_client()
    data = client.create(
        "dashboards",
        slug=slug,
        name=name or slug.replace("-", " ").title(),
        description=description,
        module=module,
        parameters=_parse_json(parameters, "--parameters") or [],
        layout=_parse_json(layout, "--layout") or {},
        tags=tags.split(",") if tags else [],
    )
    emit(data)


@app.command("update")
def update_dashboard(
    slug: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    parameters: Optional[str] = typer.Option(None, "--parameters"),
    layout: Optional[str] = typer.Option(None, "--layout"),
    tags: Optional[str] = typer.Option(None, "--tags"),
):
    """Update a dashboard."""
    client = _require_client()
    fields = dict(
        name=name, description=description, module=module,
        parameters=_parse_json(parameters, "--parameters"),
        layout=_parse_json(layout, "--layout"),
        tags=tags.split(",") if tags else None,
    )
    data = client.update("dashboards", slug, **fields)
    emit(data)


@app.command("delete")
def delete_dashboard(slug: str = typer.Argument(...)):
    """Delete a dashboard."""
    client = _require_client()
    emit(client.delete("dashboards", slug))


# ---------------------------------------------------------------------------
# Card management
# ---------------------------------------------------------------------------


@app.command("add-card")
def add_card(
    dashboard_slug: str = typer.Argument(..., help="Dashboard slug"),
    card_slug: str = typer.Argument(..., help="Card slug"),
    position: Optional[str] = typer.Option(
        None, "--position", help='Grid position JSON: {"x","y","w","h"}',
    ),
    param_overrides: Optional[str] = typer.Option(
        None, "--param-overrides",
        help='Card-param → dashboard-param map (JSON)',
    ),
    order: int = typer.Option(0, "--order"),
):
    """Place a card on a dashboard (or update its position/overrides)."""
    client = _require_client()
    data = client.action(
        "dashboards", dashboard_slug, "add-card",
        card_slug=card_slug,
        position=_parse_json(position, "--position"),
        param_overrides=_parse_json(param_overrides, "--param-overrides"),
        order=order,
    )
    emit(data)


@app.command("remove-card")
def remove_card(
    dashboard_slug: str = typer.Argument(...),
    card_slug: str = typer.Argument(...),
):
    """Remove a card from a dashboard."""
    client = _require_client()
    data = client.action_nested(
        "dashboards", dashboard_slug, "remove-card", card_slug,
    )
    emit(data)


@app.command("reorder")
def reorder_cards(
    dashboard_slug: str = typer.Argument(...),
    order: str = typer.Argument(
        ..., help="Comma-separated card slugs in desired order",
    ),
):
    """Reorder cards on a dashboard."""
    client = _require_client()
    data = client.action(
        "dashboards", dashboard_slug, "reorder",
        order=[s.strip() for s in order.split(",") if s.strip()],
    )
    emit(data)


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


@app.command("export")
def export_dashboard(
    slug: str = typer.Argument(...),
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="json"),
    params: Optional[str] = typer.Option(None, "--params"),
):
    """Export the full dashboard render payload to a JSON file."""
    import sys
    from pathlib import Path

    client = _require_client()
    query: dict[str, str] = {"format": format}
    if params:
        query["params"] = params
    qs = "&".join(f"{k}={v}" for k, v in query.items())
    resp = client._get(f"/dashboards/{slug}/export/?{qs}")
    if resp.status_code >= 400:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        raise SystemExit(1)

    Path(output).write_bytes(resp.content)
    print(f"Wrote {len(resp.content)} bytes to {output}")


@app.command("render")
def render_dashboard(
    slug: str = typer.Argument(...),
    params: Optional[str] = typer.Option(
        None, "--params", help="JSON dict of dashboard params",
    ),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Execute all cards and return the dashboard payload."""
    client = _require_client()
    payload = {"params": _parse_json(params, "--params") or {}}
    data = client.action("dashboards", slug, "render", **payload)
    emit(data, pretty=pretty, title=f"Render: {slug}")
