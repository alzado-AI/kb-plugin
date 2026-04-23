"""kb access — Row-level permission management."""

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


app = typer.Typer(help="Row-level permission management")


@app.command("show")
def show_access(
    entity_type: str = typer.Argument(..., help="Entity type (program, project, todo, etc.)"),
    identifier: str = typer.Argument(..., help="Slug or numeric ID"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show access control for an entity."""
    client = _require_client()
    data = client.show("access", f"{entity_type}/{identifier}")

    emit(data, pretty=pretty, title=f"Access: {entity_type} {identifier}")


@app.command("grant")
def grant_access(
    entity_type: str = typer.Argument(..., help="Entity type"),
    identifier: str = typer.Argument(..., help="Slug or numeric ID"),
    user: Optional[str] = typer.Option(None, "--user", help="User email"),
    group: Optional[str] = typer.Option(None, "--group", help="Group slug"),
    level: str = typer.Option("read", "--level", help="Permission level: read, comment, write"),
    propagate: bool = typer.Option(False, "--propagate", help="Propagate to child entities"),
):
    """Grant access to a user or group."""
    if not user and not group:
        emit({"error": "Must specify --user or --group"})
        raise typer.Exit(1)
    if user and group:
        emit({"error": "Specify either --user or --group, not both"})
        raise typer.Exit(1)
    if level not in ("read", "comment", "write"):
        emit({"error": f"Invalid level: {level}. Use read, comment, or write."})
        raise typer.Exit(1)

    client = _require_client()
    data = client.action(
        "access", f"{entity_type}/{identifier}", "grant",
        user=user,
        group=group,
        level=level,
        propagate="true" if propagate else None,
    )

    emit(data)


@app.command("revoke")
def revoke_access(
    entity_type: str = typer.Argument(..., help="Entity type"),
    identifier: str = typer.Argument(..., help="Slug or numeric ID"),
    user: Optional[str] = typer.Option(None, "--user", help="User email"),
    group: Optional[str] = typer.Option(None, "--group", help="Group slug"),
    propagate: bool = typer.Option(False, "--propagate", help="Revoke from child entities too"),
):
    """Revoke access from a user or group."""
    if not user and not group:
        emit({"error": "Must specify --user or --group"})
        raise typer.Exit(1)

    client = _require_client()
    data = client.action(
        "access", f"{entity_type}/{identifier}", "revoke",
        user=user,
        group=group,
        propagate="true" if propagate else None,
    )

    emit(data)


@app.command("set-visibility")
def set_visibility(
    entity_type: str = typer.Argument(..., help="Entity type"),
    identifier: str = typer.Argument(..., help="Slug or numeric ID"),
    visibility: str = typer.Option(..., "--visibility", help="org, restricted, or private"),
    org_level: Optional[str] = typer.Option(None, "--org-level", help="Base level for org: read, comment, write"),
    propagate: bool = typer.Option(False, "--propagate", help="Propagate to child entities"),
):
    """Set visibility and org_level for an entity."""
    if visibility not in ("org", "restricted", "private"):
        emit({"error": f"Invalid visibility: {visibility}"})
        raise typer.Exit(1)
    if org_level and org_level not in ("read", "comment", "write"):
        emit({"error": f"Invalid org_level: {org_level}"})
        raise typer.Exit(1)

    client = _require_client()
    data = client.action(
        "access", f"{entity_type}/{identifier}", "set-visibility",
        visibility=visibility,
        org_level=org_level,
        propagate="true" if propagate else None,
    )

    emit(data)
