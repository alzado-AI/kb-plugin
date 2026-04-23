"""kb budget — CRUD for departmental budgets."""

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

app = typer.Typer(help="Budget management (departmental spending plans)")


register_delete(app, "budgets", label="budget")

@app.command("list")
def list_budgets(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    periodo: Optional[str] = typer.Option(None, "--periodo"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List budgets with optional filters."""
    client = _require_client()
    data = client.list("budgets", module=module, periodo=periodo, estado=estado)

    emit(
        data,
        pretty=pretty,
        columns=["slug", "name", "module", "periodo", "amount_planned", "amount_executed", "estado"],
        title="Budgets",
    )


@app.command("show")
def show_budget(
    slug: str = typer.Argument(..., help="Budget slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a budget by slug."""
    client = _require_client()
    data = client.show("budgets", slug)

    emit(data, pretty=pretty, title=f"Budget: {slug}")


@app.command("create")
def create_budget(
    slug: str = typer.Argument(..., help="Budget slug (kebab-case)"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    periodo: str = typer.Option(..., "--periodo", help="Period (e.g. 2026-Q1)"),
    module_slug: Optional[str] = typer.Option(None, "--module", "-m"),
    amount_planned: Optional[str] = typer.Option(None, "--planned", help="Planned amount"),
    owner_email: Optional[str] = typer.Option(None, "--owner", "-o"),
):
    """Create a new budget."""
    client = _require_client()
    payload = dict(slug=slug, name=name or slug.replace("-", " ").title(), periodo=periodo)
    if module_slug:
        payload["module"] = module_slug
    if amount_planned:
        payload["amount_planned"] = amount_planned
    if owner_email:
        payload["owner"] = owner_email
    data = client.create("budgets", **payload)

    emit(data)


@app.command("update")
def update_budget(
    slug: str = typer.Argument(..., help="Budget slug"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    amount_planned: Optional[str] = typer.Option(None, "--planned"),
    amount_executed: Optional[str] = typer.Option(None, "--executed", help="Executed amount"),
    name: Optional[str] = typer.Option(None, "--name"),
):
    """Update a budget."""
    client = _require_client()
    updates = {}
    if estado is not None:
        updates["estado"] = estado
    if amount_planned is not None:
        updates["amount_planned"] = amount_planned
    if amount_executed is not None:
        updates["amount_executed"] = amount_executed
    if name is not None:
        updates["name"] = name
    data = client.update("budgets", slug, **updates)

    emit(data)
