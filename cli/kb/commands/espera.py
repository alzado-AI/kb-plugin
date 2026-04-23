"""kb espera — manage blocking waits for any entity (generic parent)."""

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


app = typer.Typer(help="Espera management (blocking waits)")


@app.command("list")
def list_esperas(
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Parent entity type (program, project, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (alternative to --parent-id)"),
    # Backward compat shortcuts for PM
    program: Optional[str] = typer.Option(None, "--program", "-t", hidden=True),
    project: Optional[str] = typer.Option(None, "--project", "-m", hidden=True),
    active: bool = typer.Option(False, "--active", "-a", help="Only show unresolved"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List esperas for an entity."""
    client = _require_client()
    data = client.list(
        "esperas",
        parent_type=parent_type,
        parent_id=parent_id,
        parent_slug=parent_slug,
        program=program,
        project=project,
        active="true" if active else None,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "tipo", "detalle", "source_ref", "resolved_at"],
        title="Esperas",
    )


@app.command("create")
def create_espera(
    tipo: str = typer.Argument(..., help="Wait type (e.g. feedback, aprobacion, tecnica, externa)"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Parent entity type (program, project, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (alternative to --parent-id)"),
    # Backward compat shortcuts
    program: Optional[str] = typer.Option(None, "--program", "-t", hidden=True),
    project: Optional[str] = typer.Option(None, "--project", "-m", hidden=True),
    detalle: Optional[str] = typer.Option(None, "--detalle", "-d"),
    source_ref: Optional[str] = typer.Option(None, "--source-ref", "-r"),
):
    """Create a new espera for an entity."""
    client = _require_client()
    data = client.create(
        "esperas",
        tipo=tipo,
        parent_type=parent_type,
        parent_id=parent_id,
        parent_slug=parent_slug,
        program=program,
        project=project,
        detalle=detalle,
        source_ref=source_ref,
    )

    emit(data)


@app.command("resolve")
def resolve_espera(
    espera_id: int = typer.Argument(..., help="Espera ID"),
):
    """Resolve (close) an espera."""
    client = _require_client()
    data = client.action("esperas", espera_id, "resolve")

    emit(data)
