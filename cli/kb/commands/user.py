"""kb user — User profile management."""

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


app = typer.Typer(help="User profile management")


@app.command("list")
def list_users(
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List all user profiles."""
    client = _require_client()
    data = client.list("users")

    emit(data, pretty=pretty, columns=["user_id", "display_name", "role"], title="Users")


@app.command("show")
def show_user(
    email: str = typer.Argument(..., help="User email (matched via linked person)"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a user profile by linked person email."""
    client = _require_client()
    data = client.show("users", email)

    emit(data, pretty=pretty, title=f"User: {data.get('display_name', email)}")


@app.command("set-role")
def set_role(
    email: str = typer.Argument(..., help="User email"),
    role: str = typer.Option(..., "--role", "-r", help="admin or member"),
):
    """Change a user's role."""
    if role not in ("admin", "member"):
        emit({"error": f"Invalid role '{role}'. Must be 'admin' or 'member'."})
        raise typer.Exit(1)

    client = _require_client()
    data = client.update("users", email, role=role)

    emit(data)


@app.command("create")
def create_user(
    user_id: str = typer.Argument(..., help="Auth user UUID"),
    display_name: Optional[str] = typer.Option(None, "--name"),
    role: str = typer.Option("member", "--role"),
    person_email: Optional[str] = typer.Option(None, "--person", help="Link to existing KB person by email"),
):
    """Create a user profile manually (normally auto-created via auth trigger)."""
    client = _require_client()
    data = client.create(
        "users",
        user_id=user_id,
        display_name=display_name,
        role=role,
        person_email=person_email,
    )

    emit(data)
