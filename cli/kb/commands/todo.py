"""kb todo — CRUD for todos. Formerly 'action'/'task'.

This module is importable as 'todo' for the new naming.
The CLI registers it as 'kb todo' (primary) and 'kb task'/'kb action' (backward compat).
"""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="ToDo management")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required. Set it to the Django backend URL.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_todos(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Owner email"),
    pending: bool = typer.Option(False, "--pending", help="Only pending todos"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Filter by parent entity type (program, project, need, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Filter by parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (alternative to --parent-id)"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List todos with optional filters."""
    client = _require_client()
    data = client.list(
        "todos",
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
        title="ToDos",
    )


@app.command("show")
def show_todo(
    todo_id: int = typer.Argument(..., help="ToDo ID"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show todo details."""
    client = _require_client()
    data = client.show("todos", todo_id)

    emit(data, pretty=pretty, title=f"ToDo #{todo_id}")


@app.command("create")
def create_todo(
    text: str = typer.Argument(..., help="ToDo text"),
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
    """Create a new todo."""
    client = _require_client()
    data = client.create(
        "todos",
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
def find_todo(
    keyword: str = typer.Argument(..., help="Keyword to search in todo text"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pending: bool = typer.Option(False, "--pending", help="Only pending todos"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Find todos by keyword (case-insensitive)."""
    client = _require_client()
    data = client.list(
        "todos",
        search=keyword,
        module=module,
        pending="true" if pending else None,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "text", "module", "owner", "priority", "estado"],
        title=f"ToDos matching '{keyword}'",
    )


@app.command("complete")
def complete_todo(
    todo_id: int = typer.Argument(..., help="ToDo ID"),
):
    """Mark a todo as completed."""
    client = _require_client()
    data = client.update("todos", todo_id, estado="completada")

    emit(data)


@app.command("delete")
def delete_todo(
    todo_id: Optional[int] = typer.Argument(None, help="ToDo ID (omit when using bulk flags)"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Bulk delete: parent entity type (program, project, need, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Bulk delete: parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Bulk delete: parent entity slug (alternative to --parent-id)"),
):
    """Hard-delete a todo. Prefer `complete` for audit trail.

    Cascade: elimina todos los ToDoStakeholder vinculados (add-stakeholder rows).

    Bulk: pasar `--parent-type` + `--parent-id`/`--parent-slug` sin `todo_id` borra
    todos los todos del parent. `todo_id` y los flags de parent son mutuamente excluyentes.
    """
    client = _require_client()
    has_parent = parent_type is not None or parent_id is not None or parent_slug is not None

    if todo_id is not None and has_parent:
        import sys
        print("Cannot combine todo_id with --parent-type/--parent-id/--parent-slug.", file=sys.stderr)
        raise SystemExit(1)

    if todo_id is None and not has_parent:
        import sys
        print("Provide either a todo_id or --parent-type with --parent-id/--parent-slug.", file=sys.stderr)
        raise SystemExit(1)

    if todo_id is not None:
        data = client.delete("todos", todo_id)
        emit(data)
        return

    if not parent_type or (parent_id is None and not parent_slug):
        import sys
        print("Bulk delete requires --parent-type AND (--parent-id OR --parent-slug).", file=sys.stderr)
        raise SystemExit(1)

    todos = client.list(
        "todos",
        parent_type=parent_type,
        parent_id=parent_id,
        parent_slug=parent_slug,
    )
    deleted = []
    for t in todos:
        tid = t.get("id")
        if tid is None:
            continue
        client.delete("todos", tid)
        deleted.append(tid)

    emit({"status": "deleted", "count": len(deleted), "ids": deleted})


@app.command("add-stakeholder")
def add_stakeholder(
    todo_id: int = typer.Argument(..., help="ToDo ID"),
    email: str = typer.Argument(..., help="Person email"),
    rol: Optional[str] = typer.Option(None, "--rol", "-r", help="Stakeholder role (solicitante, destinatario, reportero, interesado)"),
):
    """Add a stakeholder to a todo."""
    client = _require_client()
    data = client.action("todos", todo_id, "add-stakeholder", email=email, rol=rol)

    emit(data)


@app.command("remove-stakeholder")
def remove_stakeholder(
    todo_id: int = typer.Argument(..., help="ToDo ID"),
    email: str = typer.Argument(..., help="Person email"),
):
    """Remove a stakeholder from a todo."""
    client = _require_client()
    data = client.action("todos", todo_id, "remove-stakeholder", email=email)

    emit(data)
