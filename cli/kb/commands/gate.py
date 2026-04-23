"""kb gate — manage approval gates for any entity (generic parent)."""

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


app = typer.Typer(help="Gate management (approval checkpoints)")


@app.command("list")
def list_gates(
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Parent entity type (program, project, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (alternative to --parent-id)"),
    # Backward compat shortcuts for PM
    program: Optional[str] = typer.Option(None, "--program", "-t", hidden=True),
    project: Optional[str] = typer.Option(None, "--project", "-m", hidden=True),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List gates for an entity."""
    client = _require_client()
    data = client.list(
        "gates",
        parent_type=parent_type,
        parent_id=parent_id,
        parent_slug=parent_slug,
        program=program,
        project=project,
        estado=estado,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "gate_name", "estado", "completed_at", "notes"],
        title="Gates",
    )


@app.command("create")
def create_gate(
    gate_name: str = typer.Argument(..., help="Gate name (e.g. GATE-D1: Problema validado)"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Parent entity type (program, project, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (alternative to --parent-id)"),
    # Backward compat shortcuts
    program: Optional[str] = typer.Option(None, "--program", "-t", hidden=True),
    project: Optional[str] = typer.Option(None, "--project", "-m", hidden=True),
    doc_id: Optional[str] = typer.Option(None, "--doc-id"),
    doc_url: Optional[str] = typer.Option(None, "--doc-url"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Notes/context for the approval"),
):
    """Create a new gate for an entity."""
    client = _require_client()
    data = client.create(
        "gates",
        gate_name=gate_name,
        parent_type=parent_type,
        parent_id=parent_id,
        parent_slug=parent_slug,
        program=program,
        project=project,
        doc_id=doc_id,
        doc_url=doc_url,
        notes=notes,
    )

    emit(data)


@app.command("approve")
def approve_gate(
    gate_id: int = typer.Argument(..., help="Gate ID"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n"),
):
    """Approve a gate."""
    client = _require_client()
    data = client.action("gates", gate_id, "approve", notes=notes)

    emit(data)


@app.command("reject")
def reject_gate(
    gate_id: int = typer.Argument(..., help="Gate ID"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n"),
):
    """Reject a gate."""
    client = _require_client()
    data = client.action("gates", gate_id, "reject", notes=notes)

    emit(data)
