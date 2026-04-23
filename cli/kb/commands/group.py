"""kb group — Group management for visibility control."""

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


app = typer.Typer(help="Group management")


@app.command("list")
def list_groups(
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List all groups."""
    client = _require_client()
    data = client.list("groups")

    emit(data, pretty=pretty, columns=["id", "name", "slug", "members_count"], title="Groups")


@app.command("show")
def show_group(
    slug: str = typer.Argument(..., help="Group slug"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show group details with members."""
    client = _require_client()
    data = client.show("groups", slug)

    emit(data, pretty=pretty, title=f"Group: {data.get('name', slug)}")


@app.command("create")
def create_group(
    name: str = typer.Argument(..., help="Group name"),
    slug: Optional[str] = typer.Option(None, "--slug", "-s", help="Slug (auto-generated from name if omitted)"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
):
    """Create a new group."""
    if not slug:
        slug = name.lower().replace(" ", "-").replace("_", "-")

    client = _require_client()
    data = client.create("groups", name=name, slug=slug, description=description)

    emit(data)


@app.command("add-member")
def add_member(
    slug: str = typer.Argument(..., help="Group slug"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Member email (resolved via person -> user_profile)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="Auth user UUID directly"),
):
    """Add a user to a group."""
    if not email and not user_id:
        emit({"error": "Provide --email or --user-id"})
        raise typer.Exit(1)

    client = _require_client()
    data = client.action("groups", slug, "add-member", email=email, user_id=user_id)

    emit(data)


@app.command("remove-member")
def remove_member(
    slug: str = typer.Argument(..., help="Group slug"),
    email: Optional[str] = typer.Option(None, "--email", "-e"),
    user_id: Optional[str] = typer.Option(None, "--user-id"),
):
    """Remove a user from a group."""
    if not email and not user_id:
        emit({"error": "Provide --email or --user-id"})
        raise typer.Exit(1)

    client = _require_client()
    data = client.action("groups", slug, "remove-member", email=email, user_id=user_id)

    emit(data)
