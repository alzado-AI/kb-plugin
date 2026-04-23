"""kb content — Read and update content by ID (generic parent)."""

from pathlib import Path
from typing import Optional

import typer

from ..cache import compute_hash, write_cache_file, cache_path_from_api
from ..client import get_client
from ..output import emit


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


def _update_cache_after_push(data: dict, body: str) -> None:
    """Atomically update local cache after a successful content push.

    Uses parent_slug, parent_type, tipo and updated_at from the API response.
    No-ops silently if the response is missing required fields (e.g. older API).
    """
    parent_slug = data.get("parent_slug")
    parent_type = data.get("parent_type")
    tipo = data.get("tipo")
    content_id = data.get("id")
    updated_at = data.get("updated_at", "")

    if not all([parent_slug, parent_type, tipo, content_id]):
        return

    from .sync import update_manifest_after_push
    cache_path = cache_path_from_api(parent_type, parent_slug, tipo)
    update_manifest_after_push(
        content_id=content_id,
        body=body,
        updated_at_iso=updated_at,
        cache_path=cache_path,
        tipo=tipo,
    )


from ._crud import register_delete

app = typer.Typer(help="Content management")

register_delete(app, "content", label="content block", lookup_help="Content ID")


@app.command("list")
def list_content(
    parent_type: Optional[str] = typer.Option(None, "--parent-type",
        help="Parent entity type (program, project, need, etc.)"),
    parent_id: Optional[str] = typer.Option(None, "--parent-id"),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t"),
    pretty: bool = typer.Option(False, "--pretty"),
    with_body: bool = typer.Option(
        False, "--with-body",
        help="Include full body in list results. Default excludes body to keep "
             "output small — use `kb content show ID` to read a specific entry.",
    ),
):
    """List content records. Filter by parent_type/parent_id/tipo."""
    client = _require_client()
    kwargs = dict(parent_type=parent_type, parent_id=parent_id, tipo=tipo)
    if with_body:
        kwargs["with_body"] = 1
    data = client.list("content", **kwargs)
    emit(data, pretty=pretty, columns=["id", "tipo", "parent_type", "parent_id"],
         title="Content")


@app.command("create")
def create_content(
    parent_type: str = typer.Option(..., "--parent-type",
        help="Parent entity type (program, project, need, etc.)"),
    parent_id: int = typer.Option(..., "--parent-id"),
    tipo: str = typer.Option(..., "--tipo", "-t"),
    body: Optional[str] = typer.Option(None, "--body", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read body from file"),
):
    """Create a new content block attached to a parent entity."""
    if file:
        body = file.read_text(encoding="utf-8")
    if not body:
        emit({"error": "Provide --body or --file"})
        raise typer.Exit(1)
    client = _require_client()
    data = client.create("content", parent_type=parent_type, parent_id=parent_id,
                         tipo=tipo, body=body)
    emit(data)


@app.command("show")
def show_content(
    content_id: int = typer.Argument(..., help="Content ID"),
    full_body: bool = typer.Option(False, "--full-body", help="Show full body (default: truncated to 500 chars)"),
    full: bool = typer.Option(False, "--full", help="Alias for --full-body (matches convention used by other `show` commands)."),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a content record by ID."""
    client = _require_client()
    data = client.show("content", content_id, full_body="true" if (full_body or full) else None)

    emit(data, pretty=pretty, title=f"Content: {content_id}")


@app.command("push")
def push_content(
    content_id: Optional[int] = typer.Argument(None, help="Content ID"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="New body text"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read body from file"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Parent entity type (program, project, need, etc.; alternative to content_id)"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (requires --parent-type and --tipo)"),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t", help="Content type (e.g. negocio, tecnica, propuesta)"),
):
    """Update the body of a content record by ID or by parent slug + tipo."""
    if not body and not file:
        emit({"error": "Provide --body or --file"})
        raise typer.Exit(1)

    if file:
        body = file.read_text(encoding="utf-8")

    client = _require_client()
    if content_id:
        data = client.update("content", content_id, body=body)
    elif parent_type and parent_slug and tipo:
        data = client.create("content", action="push",
                             parent_type=parent_type, parent_slug=parent_slug,
                             tipo=tipo, body=body)
    else:
        emit({"error": "Provide content_id or --parent-type + --parent-slug + --tipo"})
        raise typer.Exit(1)

    emit(data)
    _update_cache_after_push(data, body)
