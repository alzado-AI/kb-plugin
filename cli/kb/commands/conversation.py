"""kb conversation — CRUD for human-to-Claude conversation history."""

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


from ._crud import register_delete

app = typer.Typer(help="Conversation history (human-to-Claude sessions)")


register_delete(app, "conversations", label="conversation")

@app.command("list")
def list_conversations(
    skill: Optional[str] = typer.Option(None, "--skill", "-s"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    since: Optional[str] = typer.Option(None, "--since", help="ISO date YYYY-MM-DD"),
    is_open: Optional[bool] = typer.Option(None, "--is-open/--no-is-open", help="Filter by open/closed workspace tabs"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List conversations with optional filters."""
    client = _require_client()
    data = client.list("conversations", skill=skill, module=module, since=since, is_open=is_open)

    emit(
        data,
        pretty=pretty,
        columns=["id", "uuid", "title", "fecha", "skill", "estacion", "is_open", "module", "tags"],
        title="Conversations",
    )


@app.command("show")
def show_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID"),
    full: bool = typer.Option(False, "--full", help="Include reasoning + refs"),
):
    """Show conversation details."""
    client = _require_client()
    data = client.show("conversations", conversation_id, full="true" if full else None)

    if "error" in data:
        emit(data)
        raise typer.Exit(1)
    emit(data)


@app.command("create")
def create_conversation(
    title: str = typer.Argument(..., help="Conversation title"),
    fecha: str = typer.Option(..., "--fecha", help="ISO date YYYY-MM-DD"),
    skill: Optional[str] = typer.Option(None, "--skill", "-s"),
    estacion: Optional[str] = typer.Option(None, "--estacion", "-e"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    summary: Optional[str] = typer.Option(None, "--summary"),
    reasoning: Optional[str] = typer.Option(None, "--reasoning"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
):
    """Create a new conversation record."""
    client = _require_client()
    data = client.create("conversations", title=title, fecha=fecha,
                         skill=skill, estacion=estacion, module=module,
                         summary=summary, reasoning=reasoning, tags=tags)

    emit(data)


@app.command("update")
def update_conversation(
    conversation_id: int = typer.Argument(..., help="Conversation ID"),
    summary: Optional[str] = typer.Option(None, "--summary"),
    reasoning: Optional[str] = typer.Option(None, "--reasoning"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    is_open: Optional[bool] = typer.Option(None, "--is-open/--no-is-open", help="Mark tab as open or closed"),
):
    """Update a conversation's summary, reasoning or tags."""
    client = _require_client()
    data = client.update("conversations", conversation_id,
                         summary=summary, reasoning=reasoning, tags=tags,
                         is_open=is_open)

    if "error" in data:
        emit(data)
        raise typer.Exit(1)
    emit(data)


@app.command("add-ref")
def add_ref(
    conversation_id: int = typer.Argument(..., help="Conversation ID"),
    entity_type: str = typer.Option(..., "--entity-type", help="Entity type (program, todo, etc.)"),
    entity_id: int = typer.Option(..., "--entity-id", help="Entity ID"),
    operation: str = typer.Option(..., "--operation", help="created|updated|read|deleted"),
    note: Optional[str] = typer.Option(None, "--note"),
):
    """Add a reference to a KB entity touched during this conversation."""
    client = _require_client()
    data = client.action("conversations", conversation_id, "add-ref",
                         entity_type=entity_type, entity_id=entity_id,
                         operation=operation, note=note)

    emit(data)


@app.command("search")
def search_conversations(
    keyword: str = typer.Argument(..., help="Search keyword"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Search conversations by keyword (FTS on title + summary + reasoning)."""
    client = _require_client()
    data = client.list("conversations", search=keyword)

    emit(
        data,
        pretty=pretty,
        columns=["id", "uuid", "title", "fecha", "skill", "estacion", "module"],
        title=f"Conversations matching '{keyword}'",
    )


@app.command("trace")
def trace_entity(
    entity_type: str = typer.Option(..., "--entity-type", help="Entity type to trace"),
    entity_id: int = typer.Option(..., "--entity-id", help="Entity ID to trace"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Reverse lookup: find all conversations that touched a specific KB entity."""
    client = _require_client()
    data = client.list("conversations", trace_entity_type=entity_type,
                       trace_entity_id=entity_id)

    emit(
        data,
        pretty=pretty,
        columns=["id", "title", "fecha", "skill", "estacion", "module"],
        title=f"Conversations touching {entity_type}:{entity_id}",
    )
