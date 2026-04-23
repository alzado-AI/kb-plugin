"""kb cashflow — CRUD for cash flow items."""

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

app = typer.Typer(help="Cashflow management (projected and actual entries)")


register_delete(app, "cashflows", label="cashflow item")
register_update(app, "cashflows", label="cashflow item")

@app.command("list")
def list_items(
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t", help="ingreso or egreso"),
    budget: Optional[str] = typer.Option(None, "--budget", "-b", help="Budget slug"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    company: Optional[str] = typer.Option(None, "--company", help="Filter by company name"),
    overdue: bool = typer.Option(False, "--overdue", help="Show only overdue items"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List cashflow items."""
    client = _require_client()
    data = client.list(
        "cashflows", tipo=tipo, budget=budget, estado=estado,
        category=category, company=company, overdue=overdue or None,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "tipo", "amount", "fecha", "category", "estado", "company", "due_date"],
        title="Cashflow Items",
    )


@app.command("show")
def show_item(
    item_id: int = typer.Argument(..., help="Cashflow item ID"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a cashflow item by ID."""
    client = _require_client()
    data = client.show("cashflows", item_id)

    emit(data, pretty=pretty, title=f"Cashflow Item #{item_id}")


@app.command("create")
def create_item(
    tipo: str = typer.Argument(..., help="Type: ingreso or egreso"),
    amount: str = typer.Argument(..., help="Amount"),
    fecha: str = typer.Argument(..., help="Date (YYYY-MM-DD)"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    estado: str = typer.Option("proyectado", "--estado", "-e", help="proyectado, confirmado, ejecutado"),
    source_ref: Optional[str] = typer.Option(None, "--source-ref", "-r"),
    budget_slug: Optional[str] = typer.Option(None, "--budget", "-b", help="Budget slug"),
    company: Optional[str] = typer.Option(None, "--company", help="Company name"),
    opportunity: Optional[str] = typer.Option(None, "--opportunity", help="Opportunity slug"),
    due_date: Optional[str] = typer.Option(None, "--due-date", help="Due date (YYYY-MM-DD)"),
    description: Optional[str] = typer.Option(None, "--description"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    external_source: Optional[str] = typer.Option(None, "--external-source"),
    invoice: Optional[str] = typer.Option(None, "--invoice", help="Invoice number"),
):
    """Create a new cashflow item."""
    client = _require_client()
    payload = dict(tipo=tipo, amount=amount, fecha=fecha, estado=estado)
    if category:
        payload["category"] = category
    if source_ref:
        payload["source_ref"] = source_ref
    if budget_slug:
        payload["budget"] = budget_slug
    if company:
        payload["company"] = company
    if opportunity:
        payload["opportunity"] = opportunity
    if due_date:
        payload["due_date"] = due_date
    if description:
        payload["description"] = description
    if external_id:
        payload["external_id"] = external_id
    if external_source:
        payload["external_source"] = external_source
    if invoice:
        payload["invoice"] = invoice
    data = client.create("cashflows", **payload)

    emit(data)
