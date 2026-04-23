"""kb invoice — CRUD for invoices."""

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

app = typer.Typer(help="Invoice management")


register_delete(app, "invoices", label="invoice")

@app.command("list")
def list_invoices(
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Filter by company name"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e", help="Filter by estado"),
    overdue: bool = typer.Option(False, "--overdue", help="Show only overdue invoices"),
    pretty: bool = typer.Option(False, "--pretty", "-p", help="Rich table output"),
):
    """List invoices with optional filters."""
    client = _require_client()
    data = client.list(
        "invoices", company=company, estado=estado,
        overdue="true" if overdue else None,
    )

    emit(
        data,
        pretty=pretty,
        columns=["number", "company", "amount", "currency", "estado", "issue_date", "due_date"],
        title="Invoices",
    )


@app.command("create")
def create_invoice(
    number: str = typer.Argument(..., help="Invoice number"),
    amount: float = typer.Option(..., "--amount", "-a", help="Invoice amount"),
    issue_date: str = typer.Option(..., "--issue-date", help="Issue date (YYYY-MM-DD)"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Company name"),
    due_date: Optional[str] = typer.Option(None, "--due-date", help="Due date (YYYY-MM-DD)"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Invoice title"),
    currency: Optional[str] = typer.Option(None, "--currency", help="Currency code (e.g. USD, CLP)"),
    opportunity: Optional[str] = typer.Option(None, "--opportunity", help="Opportunity slug"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    external_source: Optional[str] = typer.Option(None, "--external-source"),
):
    """Create a new invoice."""
    client = _require_client()
    data = client.create(
        "invoices",
        number=number,
        amount=amount,
        issue_date=issue_date,
        company=company,
        due_date=due_date,
        title=title,
        currency=currency,
        opportunity=opportunity,
        external_id=external_id,
        external_source=external_source,
    )

    emit(data)


@app.command("update")
def update_invoice(
    number: str = typer.Argument(..., help="Invoice number"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    paid_date: Optional[str] = typer.Option(None, "--paid-date", help="Payment date (YYYY-MM-DD)"),
    paid_amount: Optional[float] = typer.Option(None, "--paid-amount"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
):
    """Update an invoice."""
    client = _require_client()
    updates = {}
    if estado is not None:
        updates["estado"] = estado
    if paid_date is not None:
        updates["paid_date"] = paid_date
    if paid_amount is not None:
        updates["paid_amount"] = paid_amount
    if notes is not None:
        updates["notes"] = notes
    if external_id is not None:
        updates["external_id"] = external_id
    data = client.update("invoices", number, **updates)

    emit(data)


@app.command("show")
def show_invoice(
    number: str = typer.Argument(..., help="Invoice number"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show an invoice by number."""
    client = _require_client()
    data = client.show("invoices", number)

    emit(data, pretty=pretty, title=f"Invoice: {number}")
