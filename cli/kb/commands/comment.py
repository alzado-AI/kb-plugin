"""kb comment — Row-level comments on any entity."""

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


app = typer.Typer(help="Row-level comments")


@app.command("add")
def add_comment(
    entity_type: str = typer.Argument(..., help="Entity type (program, project, todo, etc.)"),
    identifier: str = typer.Argument(..., help="Slug or numeric ID"),
    body: str = typer.Option(..., "--body", help="Comment text"),
):
    """Add a comment to an entity. Requires comment or write permission."""
    client = _require_client()
    data = client.action(
        "comments", None, "add",
        entity_type=entity_type,
        slug_or_id=identifier,
        body=body,
    )

    emit(data)


@app.command("list")
def list_comments(
    entity_type: str = typer.Argument(..., help="Entity type"),
    identifier: str = typer.Argument(..., help="Slug or numeric ID"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List comments on an entity. Requires read permission."""
    client = _require_client()
    data = client.list(
        "comments",
        entity_type=entity_type,
        slug_or_id=identifier,
    )

    emit(data, pretty=pretty, columns=["id", "author_name", "body", "created_at"], title="Comments")


@app.command("delete")
def delete_comment(
    comment_id: int = typer.Argument(..., help="Comment ID"),
):
    """Delete a comment by ID. Only the author or admin can delete."""
    client = _require_client()
    data = client.delete("comments", comment_id)

    emit(data)
