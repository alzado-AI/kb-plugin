"""kb account-plan — CRUD for customer account plans."""

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

app = typer.Typer(help="Account plan management (strategic customer plans)")


register_delete(app, "account-plans", label="account plan")

@app.command("list")
def list_plans(
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Filter by company name"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List account plans."""
    client = _require_client()
    data = client.list("account-plans", company=company, estado=estado)

    emit(
        data,
        pretty=pretty,
        columns=["slug", "title", "company", "periodo", "estado", "owner"],
        title="Account Plans",
    )


@app.command("show")
def show_plan(
    slug: str = typer.Argument(..., help="Account plan slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show an account plan by slug."""
    client = _require_client()
    data = client.show("account-plans", slug)

    emit(data, pretty=pretty, title=f"Account Plan: {slug}")


@app.command("create")
def create_plan(
    slug: str = typer.Argument(..., help="Plan slug (kebab-case)"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    company_name: Optional[str] = typer.Option(None, "--company", "-c"),
    periodo: Optional[str] = typer.Option(None, "--periodo", help="Period (e.g. 2026-Q1)"),
    owner_email: Optional[str] = typer.Option(None, "--owner", "-o"),
    strategy: Optional[str] = typer.Option(None, "--strategy", "-s", help="Strategy summary"),
):
    """Create a new account plan."""
    client = _require_client()
    payload = dict(slug=slug, title=title or slug.replace("-", " ").title())
    if company_name:
        payload["company"] = company_name
    if periodo:
        payload["periodo"] = periodo
    if owner_email:
        payload["owner"] = owner_email
    if strategy:
        payload["strategy_summary"] = strategy
    data = client.create("account-plans", **payload)

    emit(data)


@app.command("update")
def update_plan(
    slug: str = typer.Argument(..., help="Plan slug"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    strategy: Optional[str] = typer.Option(None, "--strategy", "-s"),
    periodo: Optional[str] = typer.Option(None, "--periodo"),
):
    """Update an account plan."""
    client = _require_client()
    updates = {}
    if estado is not None:
        updates["estado"] = estado
    if title is not None:
        updates["title"] = title
    if strategy is not None:
        updates["strategy_summary"] = strategy
    if periodo is not None:
        updates["periodo"] = periodo
    data = client.update("account-plans", slug, **updates)

    emit(data)


@app.command("link")
def link_opportunity(
    slug: str = typer.Argument(..., help="Account plan slug"),
    opportunity: str = typer.Option(..., "--opportunity", help="Opportunity slug"),
    priority: Optional[str] = typer.Option(None, "--priority", help="high, medium, low"),
):
    """Link an opportunity to an account plan."""
    client = _require_client()
    payload = {"opportunity": opportunity}
    if priority:
        payload["priority"] = priority
    data = client._request(
        "POST", f"account-plans/{slug}/link-opportunity/", json=payload,
    )

    emit(data)


@app.command("unlink")
def unlink_opportunity(
    slug: str = typer.Argument(..., help="Account plan slug"),
    opportunity: str = typer.Option(..., "--opportunity", help="Opportunity slug"),
):
    """Unlink an opportunity from an account plan."""
    client = _require_client()
    data = client._request(
        "DELETE", f"account-plans/{slug}/link-opportunity/{opportunity}/",
    )

    emit(data)
