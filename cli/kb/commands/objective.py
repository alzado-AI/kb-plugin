"""kb objective — CRUD for strategic objectives."""

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


app = typer.Typer(help="Objective management")


@app.command("list")
def list_objectives(
    semester: Optional[str] = typer.Option(None, "--semester", "-s"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List objectives with optional semester filter."""
    client = _require_client()
    data = client.list("objectives", semester=semester)

    emit(
        data,
        pretty=pretty,
        columns=["id", "name", "metric", "baseline", "target", "semester", "programs_count"],
        title="Objectives",
    )


@app.command("show")
def show_objective(
    objective_id: int = typer.Argument(..., help="Objective ID"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show an objective by ID, including linked programs."""
    client = _require_client()
    data = client.show("objectives", objective_id)

    emit(data, pretty=pretty, title=f"Objective: {objective_id}")


@app.command("create")
def create_objective(
    name: str = typer.Argument(..., help="Objective name"),
    metric: Optional[str] = typer.Option(None, "--metric", "-m"),
    baseline: Optional[str] = typer.Option(None, "--baseline", "-b"),
    target: Optional[str] = typer.Option(None, "--target", "-t"),
    semester: str = typer.Option("2026-S1", "--semester", "-s"),
):
    """Create a new objective."""
    client = _require_client()
    data = client.create("objectives", name=name, metric=metric, baseline=baseline,
                         target=target, semester=semester)

    emit(data)


@app.command("update")
def update_objective(
    objective_id: int = typer.Argument(..., help="Objective ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    metric: Optional[str] = typer.Option(None, "--metric", "-m"),
    baseline: Optional[str] = typer.Option(None, "--baseline", "-b"),
    target: Optional[str] = typer.Option(None, "--target", "-t"),
    semester: Optional[str] = typer.Option(None, "--semester", "-s"),
):
    """Update an existing objective."""
    client = _require_client()
    data = client.update("objectives", objective_id, name=name, metric=metric,
                         baseline=baseline, target=target, semester=semester)

    emit(data)


@app.command("delete")
def delete_objective(
    objective_id: int = typer.Argument(..., help="Objective ID"),
):
    """Delete an objective (unlinks programs via cascade on program_objectives)."""
    client = _require_client()
    data = client.delete("objectives", objective_id)

    emit({"ok": True, "deleted": objective_id})
