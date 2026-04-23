"""kb module — CRUD for product modules."""

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

app = typer.Typer(help="Module management")


register_delete(app, "modules", label="module")
register_update(app, "modules", label="module")

@app.command("list")
def list_modules(
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List all modules."""
    client = _require_client()
    data = client.list("modules")

    emit(
        data,
        pretty=pretty,
        columns=["id", "slug", "display_name", "owner_pm", "em"],
        title="Modules",
    )


@app.command("show")
def show_module(
    slug: str = typer.Argument(..., help="Module slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a module by slug."""
    client = _require_client()
    data = client.show("modules", slug)

    emit(data, pretty=pretty)


@app.command("create")
def create_module(
    slug: str = typer.Argument(..., help="Module slug (english, kebab-case)"),
    display_name: Optional[str] = typer.Option(None, "--name", "-n", help="Display name"),
    owner_pm: Optional[str] = typer.Option(None, "--owner-pm", help="Owner PM email"),
    em: Optional[str] = typer.Option(None, "--em", help="Engineering Manager email"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Create a new module."""
    client = _require_client()
    data = client.create(
        "modules",
        slug=slug,
        display_name=display_name or slug.replace("-", " ").title(),
        owner_pm=owner_pm,
        em=em,
    )

    emit(data, pretty=pretty)
