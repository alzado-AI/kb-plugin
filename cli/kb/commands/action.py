"""kb task — CRUD for tasks (to-dos). Formerly 'action'.

This module is importable as both 'action' and 'task' for backward compatibility.
The CLI registers it as both 'kb task' (primary) and 'kb action' (backward compat).
"""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Task management")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required. Set it to the Django backend URL.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_tasks(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Owner email"),
    pending: bool = typer.Option(False, "--pending", help="Only pending tasks"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Filter by parent entity type (program, project, need, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Filter by parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (alternative to --parent-id)"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List tasks with optional filters."""
    client = _require_client()
    data = client.list(
        "tasks",
        module=module,
        owner=owner,
        pending="true" if pending else None,
        priority=priority,
        parent_type=parent_type,
        parent_id=parent_id,
        parent_slug=parent_slug,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "text", "module", "owner", "priority", "estado", "parent_type", "parent_id"],
        title="Tasks",
    )


@app.command("show")
def show_task(
    task_id: int = typer.Argument(..., help="Task ID"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show task details."""
    client = _require_client()
    data = client.show("tasks", task_id)

    emit(data, pretty=pretty, title=f"Task #{task_id}")


@app.command("create")
def create_task(
    text: str = typer.Argument(..., help="Task text"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    owner_email: Optional[str] = typer.Option(None, "--owner", "-o"),
    priority: str = typer.Option("media", "--priority", "-p"),
    source: Optional[str] = typer.Option(None, "--source", "-s"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Parent entity type (program, project, need, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (alternative to --parent-id)"),
    force: bool = typer.Option(False, "--force", help="Skip duplicate check"),
):
    """Create a new task."""
    client = _require_client()
    data = client.create(
        "tasks",
        text=text,
        module=module,
        owner_email=owner_email,
        priority=priority,
        source=source,
        tags=tags,
        parent_type=parent_type,
        parent_id=parent_id,
        parent_slug=parent_slug,
        force="true" if force else None,
    )

    emit(data)


@app.command("find")
def find_task(
    keyword: str = typer.Argument(..., help="Keyword to search in task text"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pending: bool = typer.Option(False, "--pending", help="Only pending tasks"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Find tasks by keyword (case-insensitive)."""
    client = _require_client()
    data = client.list(
        "tasks",
        search=keyword,
        module=module,
        pending="true" if pending else None,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "text", "module", "owner", "priority", "estado"],
        title=f"Tasks matching '{keyword}'",
    )


@app.command("complete")
def complete_task(
    task_id: int = typer.Argument(..., help="Task ID"),
):
    """Mark a task as completed."""
    client = _require_client()
    data = client.update("tasks", task_id, estado="completada")

    emit(data)


@app.command("add-stakeholder")
def add_stakeholder(
    task_id: int = typer.Argument(..., help="Task ID"),
    email: str = typer.Argument(..., help="Person email"),
    rol: Optional[str] = typer.Option(None, "--rol", "-r", help="Stakeholder role (solicitante, destinatario, reportero, interesado)"),
):
    """Add a stakeholder to a task."""
    client = _require_client()
    data = client.action("tasks", task_id, "add-stakeholder", email=email, rol=rol)

    emit(data)


@app.command("remove-stakeholder")
def remove_stakeholder(
    task_id: int = typer.Argument(..., help="Task ID"),
    email: str = typer.Argument(..., help="Person email"),
):
    """Remove a stakeholder from a task."""
    client = _require_client()
    data = client.action("tasks", task_id, "remove-stakeholder", email=email)

    emit(data)
