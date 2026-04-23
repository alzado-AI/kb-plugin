"""kb card — CRUD + execute for BI cards."""

from typing import Optional

import typer

from ..output import emit
from ._crud import _client_or_die as _require_client, _parse_json

app = typer.Typer(help="Card management (BI)")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@app.command("list")
def list_cards(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    viz_type: Optional[str] = typer.Option(None, "--viz-type"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List cards."""
    client = _require_client()
    data = client.list("cards", module=module, viz_type=viz_type)
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "viz_type", "module", "updated_at"],
        title="Cards",
    )


@app.command("show")
def show_card(
    slug: str = typer.Argument(...),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a card."""
    client = _require_client()
    data = client.show("cards", slug)
    emit(data, pretty=pretty, title=f"Card: {slug}")


@app.command("create")
def create_card(
    slug: str = typer.Argument(..., help="Card slug (kebab-case)"),
    data_source: str = typer.Option(
        ..., "--data-source",
        help='JSON: {"type":"workflow","config":{"pipeline_slug":"...","input":{...}}}',
    ),
    viz_type: str = typer.Option(..., "--viz-type", help="table|pivot|number|text|…"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    description: str = typer.Option("", "--description", "-d"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    parameters: Optional[str] = typer.Option(None, "--parameters", help="JSON list"),
    default_params: Optional[str] = typer.Option(None, "--default-params", help="JSON dict"),
    viz_config: Optional[str] = typer.Option(None, "--viz-config", help="JSON dict"),
    cache_ttl: Optional[int] = typer.Option(None, "--cache-ttl"),
    tags: Optional[str] = typer.Option(None, "--tags"),
):
    """Create a card.

    data_source.type must be 'workflow' — Phase 2 unified all data sources
    under workflows. For KB queries use the canonical pipeline 'kb-query';
    for external CLIs create a new Pipeline with a 'code' step. Pipelines
    that feed cards may only contain deterministic step types
    (code/router/foreach), never agent/approval.
    """
    client = _require_client()
    body = dict(
        slug=slug,
        name=name or slug.replace("-", " ").title(),
        description=description,
        module=module,
        data_source=_parse_json(data_source, "--data-source"),
        parameters=_parse_json(parameters, "--parameters") or [],
        default_params=_parse_json(default_params, "--default-params") or {},
        viz_type=viz_type,
        viz_config=_parse_json(viz_config, "--viz-config") or {},
        cache_ttl_seconds=cache_ttl,
        tags=tags.split(",") if tags else [],
    )
    emit(client.create("cards", **body))


@app.command("update")
def update_card(
    slug: str = typer.Argument(...),
    data_source: Optional[str] = typer.Option(None, "--data-source"),
    viz_type: Optional[str] = typer.Option(None, "--viz-type"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    parameters: Optional[str] = typer.Option(None, "--parameters"),
    default_params: Optional[str] = typer.Option(None, "--default-params"),
    viz_config: Optional[str] = typer.Option(None, "--viz-config"),
    cache_ttl: Optional[int] = typer.Option(None, "--cache-ttl"),
    tags: Optional[str] = typer.Option(None, "--tags"),
):
    """Update a card."""
    client = _require_client()
    fields = dict(
        name=name, description=description, module=module, viz_type=viz_type,
        cache_ttl_seconds=cache_ttl,
        data_source=_parse_json(data_source, "--data-source"),
        parameters=_parse_json(parameters, "--parameters"),
        default_params=_parse_json(default_params, "--default-params"),
        viz_config=_parse_json(viz_config, "--viz-config"),
        tags=tags.split(",") if tags else None,
    )
    emit(client.update("cards", slug, **fields))


@app.command("delete")
def delete_card(slug: str = typer.Argument(...)):
    """Delete a card."""
    client = _require_client()
    emit(client.delete("cards", slug))


# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------


@app.command("execute")
def execute_card(
    slug: str = typer.Argument(...),
    params: Optional[str] = typer.Option(
        None, "--params", help="JSON dict of params",
    ),
    force: bool = typer.Option(
        False, "--force", help="Bypass cache and re-run",
    ),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Run the card and print the resulting rows."""
    client = _require_client()
    body = dict(
        params=_parse_json(params, "--params") or {},
        force_refresh=force,
    )
    data = client.action("cards", slug, "execute", **body)
    emit(data, pretty=pretty, title=f"Execute: {slug}")


@app.command("result")
def card_result(
    slug: str = typer.Argument(...),
    params_hash: Optional[str] = typer.Option(None, "--params-hash"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Get the latest CardRun for this card + viewer."""
    client = _require_client()
    data = client.get(
        f"cards/{slug}/result",
        params_hash=params_hash,
    )
    emit(data, pretty=pretty, title=f"Result: {slug}")


@app.command("runs")
def list_runs(
    slug: str = typer.Argument(...),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List recent CardRuns for this card + viewer (metadata only)."""
    client = _require_client()
    data = client.get(f"cards/{slug}/runs")
    emit(data, pretty=pretty, title=f"Runs: {slug}")


@app.command("export")
def export_card(
    slug: str = typer.Argument(...),
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    format: str = typer.Option("csv", "--format", "-f", help="csv | json"),
    params: Optional[str] = typer.Option(None, "--params"),
    force: bool = typer.Option(False, "--force", help="Bypass cache"),
):
    """Export card rows to a file (csv or json)."""
    import sys
    from pathlib import Path

    client = _require_client()
    query: dict[str, str] = {"format": format}
    if params:
        query["params"] = params
    if force:
        query["force_refresh"] = "1"

    qs = "&".join(f"{k}={v}" for k, v in query.items())
    resp = client._get(f"/cards/{slug}/export/?{qs}")
    if resp.status_code >= 400:
        print(f"Error {resp.status_code}: {resp.text}", file=sys.stderr)
        raise SystemExit(1)

    Path(output).write_bytes(resp.content)
    print(f"Wrote {len(resp.content)} bytes to {output}")
