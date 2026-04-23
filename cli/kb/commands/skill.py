"""kb skill — Skill management (list, show)."""

import sys
from typing import Optional

import typer

from ..client import get_client
from ..output import emit


def _require_client():
    client = get_client()
    if not client:
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


from ._crud import register_delete

app = typer.Typer(help="Skill management")


register_delete(app, "skills", label="skill")

# ---------------------------------------------------------------------------
# Skill CRUD
# ---------------------------------------------------------------------------


@app.command("list")
def list_skills(
    domain: Optional[str] = typer.Option(None, "--domain", "-d"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    pretty: bool = typer.Option(False, "--pretty"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results to show"),
    with_body: bool = typer.Option(
        False, "--with-body",
        help="Include `definition_body`. Default excludes it — use `kb skill show SLUG`.",
    ),
):
    """List skills."""
    client = _require_client()
    params = {}
    if domain:
        params["domain"] = domain
    if estado:
        params["estado"] = estado
    if with_body:
        params["with_body"] = 1
    data = client.list("skills", **params)
    if limit and isinstance(data, list):
        data = data[:limit]
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "domain", "estado", "owner_id", "config_hash"],
        title="Skills",
    )


@app.command("show")
def show_skill(
    slug: str = typer.Argument(..., help="Skill slug"),
    pretty: bool = typer.Option(True, "--pretty/--no-pretty"),
):
    """Show skill details."""
    client = _require_client()
    data = client.get(f"skills/{slug}")
    emit(data, pretty=pretty)
