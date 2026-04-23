"""kb lint — validate KB consistency against the database."""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


app = typer.Typer(help="Lint and heal commands")


@app.command("check")
def lint_check(
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Filter by module slug"),
    track_slug: Optional[str] = typer.Option(None, "--program", "-t", help="Filter to a specific program and its projects"),
    mission_slug: Optional[str] = typer.Option(None, "--project", help="Filter to a specific project and its parent program"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Validate KB data consistency in the database."""
    client = _require_client()
    params = {}
    if module:
        params["module"] = module
    if track_slug:
        params["program"] = track_slug
    if mission_slug:
        params["project"] = mission_slug
    resp = client._get("/lint/check/", params=params)
    data = resp.json()

    emit(data, pretty=pretty, title="KB Lint Results")

    errors = data.get("errors", [])
    warnings = data.get("warnings", [])
    if errors:
        raise typer.Exit(2)
    elif warnings:
        raise typer.Exit(1)


@app.command("heal")
def lint_heal(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be fixed without applying"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Auto-fix structural issues in the database (safe operations only).

    Fixes:
    - Actions without module -> assigns to module based on text matching
    - Tracks with estado=None -> sets to 'en-evaluacion'
    - Missions with estado=None -> sets to 'exploratoria'
    """
    client = _require_client()
    resp = client._post("/lint/heal/", json={"dry_run": dry_run})
    data = resp.json()

    emit(data, pretty=pretty, title="KB Heal Results")
