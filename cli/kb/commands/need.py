"""kb need — CRUD for customer needs (formerly jobs-to-be-done)."""

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


app = typer.Typer(help="Need management (customer needs)")


@app.command("list")
def list_needs(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List needs with optional module filter."""
    client = _require_client()
    data = client.list("needs", module=module)

    emit(
        data,
        pretty=pretty,
        columns=["slug", "title", "module", "position", "programs_count"],
        title="Needs",
    )


@app.command("show")
def show_need(
    slug: str = typer.Argument(..., help="Need slug"),
    signals: bool = typer.Option(False, "--signals", "-s", help="Include linked programs and signals"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a need by slug, including linked programs."""
    client = _require_client()
    data = client.show("needs", slug, signals="true" if signals else None)

    emit(data, pretty=pretty, title=f"Need: {slug}")


@app.command("create")
def create_need(
    slug: str = typer.Argument(..., help="Need slug (kebab-case)"),
    module: str = typer.Option(..., "--module", "-m", help="Module slug"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    position: Optional[int] = typer.Option(None, "--position", "-n"),
):
    """Create a new need."""
    client = _require_client()
    data = client.create("needs", slug=slug, module=module,
                         title=title or slug.replace("-", " ").title(),
                         description=description, position=position)

    emit(data)


@app.command("update")
def update_need(
    slug: str = typer.Argument(..., help="Need slug"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    position: Optional[int] = typer.Option(None, "--position", "-n"),
):
    """Update a need."""
    client = _require_client()
    data = client.update("needs", slug, title=title, description=description,
                         position=position)

    emit(data)


@app.command("delete")
def delete_need(
    slug: str = typer.Argument(..., help="Need slug"),
):
    """Delete a need (unlinks programs via cascade on program_needs)."""
    client = _require_client()
    data = client.delete("needs", slug)

    emit({"ok": True, "deleted": slug})
