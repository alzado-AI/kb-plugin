"""kb team — CRUD for teams."""

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


from ._crud import register_delete, register_update

app = typer.Typer(help="Team management")


register_delete(app, "teams", label="team")
register_update(app, "teams", label="team")

@app.command("list")
def list_teams(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List teams with optional module filter."""
    client = _require_client()
    data = client.list("teams", module=module)

    emit(
        data,
        pretty=pretty,
        columns=["id", "name", "tipo", "em", "module", "members"],
        title="Teams",
    )


@app.command("show")
def show_team(
    name: str = typer.Argument(..., help="Team name (partial match)"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a team by name."""
    client = _require_client()
    data = client.show("teams", name)

    emit(data, pretty=pretty, title=f"Team: {name}")


@app.command("create")
def create_team(
    name: str = typer.Argument(..., help="Team name"),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    em_email: Optional[str] = typer.Option(None, "--em", help="EM email"),
):
    """Create a new team."""
    client = _require_client()
    data = client.create(
        "teams",
        name=name,
        tipo=tipo,
        module=module,
        em=em_email,
    )

    emit(data)


@app.command("add-member")
def add_member(
    team_name: str = typer.Argument(..., help="Team name"),
    email: str = typer.Argument(..., help="Person email"),
):
    """Add a member to a team."""
    client = _require_client()
    data = client.action("teams", team_name, "add-member", email=email)

    emit(data)
