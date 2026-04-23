"""kb contract — CRUD for contracts."""

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

app = typer.Typer(help="Contract management")


register_delete(app, "contracts", label="contract")

@app.command("list")
def list_contracts(
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Filter by company name"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e", help="Filter by estado"),
    por_renovar: bool = typer.Option(False, "--por-renovar", help="Show contracts up for renewal"),
    pretty: bool = typer.Option(False, "--pretty", "-p", help="Rich table output"),
):
    """List contracts with optional filters."""
    client = _require_client()
    data = client.list(
        "contracts", company=company, estado=estado,
        por_renovar="true" if por_renovar else None,
    )

    emit(
        data,
        pretty=pretty,
        columns=["slug", "title", "company", "estado", "tipo", "amount", "start_date", "end_date"],
        title="Contracts",
    )


@app.command("create")
def create_contract(
    slug: str = typer.Argument(..., help="Contract slug (kebab-case)"),
    title: str = typer.Option(..., "--title", "-t", help="Contract title"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Company name"),
    tipo: Optional[str] = typer.Option(None, "--tipo", help="Contract type"),
    amount: Optional[float] = typer.Option(None, "--amount", "-a", help="Contract amount"),
    currency: Optional[str] = typer.Option(None, "--currency", help="Currency code (e.g. USD, CLP)"),
    billing_frequency: Optional[str] = typer.Option(None, "--billing-frequency", help="Billing frequency"),
    start_date: Optional[str] = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = typer.Option(None, "--end-date", help="End date (YYYY-MM-DD)"),
    renewal_date: Optional[str] = typer.Option(None, "--renewal-date", help="Renewal date (YYYY-MM-DD)"),
    opportunity: Optional[str] = typer.Option(None, "--opportunity", help="Opportunity slug"),
    owner: Optional[str] = typer.Option(None, "--owner", help="Owner email"),
):
    """Create a new contract."""
    client = _require_client()
    data = client.create(
        "contracts",
        slug=slug,
        title=title,
        company=company,
        tipo=tipo,
        amount=amount,
        currency=currency,
        billing_frequency=billing_frequency,
        start_date=start_date,
        end_date=end_date,
        renewal_date=renewal_date,
        opportunity=opportunity,
        owner=owner,
    )

    emit(data)


@app.command("update")
def update_contract(
    slug: str = typer.Argument(..., help="Contract slug"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    cancel_reason: Optional[str] = typer.Option(None, "--cancel-reason"),
    cancelled_at: Optional[str] = typer.Option(None, "--cancelled-at", help="Cancellation date (YYYY-MM-DD)"),
    renewal_date: Optional[str] = typer.Option(None, "--renewal-date", help="Renewal date (YYYY-MM-DD)"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
):
    """Update a contract."""
    client = _require_client()
    updates = {}
    if estado is not None:
        updates["estado"] = estado
    if cancel_reason is not None:
        updates["cancel_reason"] = cancel_reason
    if cancelled_at is not None:
        updates["cancelled_at"] = cancelled_at
    if renewal_date is not None:
        updates["renewal_date"] = renewal_date
    if notes is not None:
        updates["notes"] = notes
    if external_id is not None:
        updates["external_id"] = external_id
    data = client.update("contracts", slug, **updates)

    emit(data)


@app.command("show")
def show_contract(
    slug: str = typer.Argument(..., help="Contract slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a contract by slug."""
    client = _require_client()
    data = client.show("contracts", slug)

    emit(data, pretty=pretty, title=f"Contract: {slug}")
