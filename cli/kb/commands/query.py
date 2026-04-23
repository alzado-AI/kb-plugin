"""kb query — cross-cutting queries for strategic views."""

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


app = typer.Typer(help="Cross-cutting queries")


@app.command("coverage")
def coverage(
    program_slug: str = typer.Argument(..., help="Program slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show projects covering a program + identify gaps."""
    client = _require_client()
    data = client.query("coverage", program_slug=program_slug)

    emit(data, pretty=pretty, title=f"Coverage: {program_slug}")


@app.command("cross-programs")
def cross_programs(
    project_slug: str = typer.Argument(..., help="Project slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show all programs that reference a project."""
    client = _require_client()
    data = client.query("cross-programs", project_slug=project_slug)

    emit(data, pretty=pretty, title=f"Cross-programs: {project_slug}")


@app.command("gaps")
def gaps(
    objective: Optional[str] = typer.Option(None, "--objective", "-o"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Find objectives without program coverage, programs without projects, etc."""
    client = _require_client()
    data = client.query("gaps", objective=objective)

    emit(data, pretty=pretty, title="Gaps Analysis")


@app.command("active-esperas")
def active_esperas(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List all unresolved esperas, optionally filtered by module."""
    client = _require_client()
    data = client.query("active-esperas", module=module)
    results = data if isinstance(data, list) else data.get("results", data)

    emit(
        results,
        pretty=pretty,
        columns=["id", "tipo", "owner_type", "owner_slug", "detalle", "created_at"],
        title="Active Esperas",
    )


@app.command("scanner-summary")
def scanner_summary(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Consolidated snapshot for trabajo-scanner: status + programs + projects + todos + questions + gaps + objectives + teams + people in one call."""
    client = _require_client()
    data = client.query("scanner-summary", module=module)

    emit(data, pretty=pretty, title="Scanner Summary")


@app.command("need-evidence")
def need_evidence(
    need_slug: str = typer.Argument(..., help="Need slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show all evidence linked to a need: programs (M2M) + signals."""
    client = _require_client()
    data = client.query("need-evidence", need_slug=need_slug)

    emit(data, pretty=pretty, title=f"Need Evidence: {need_slug}")


@app.command("pipeline-status")
def pipeline_status(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show pipeline status: programs/projects by estacion with blockers."""
    client = _require_client()
    data = client.query("pipeline-status", module=module)

    emit(data, pretty=pretty, title="Pipeline Status")
