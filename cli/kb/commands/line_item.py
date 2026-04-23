"""kb line-item — manage line items on invoices, contracts, opportunities."""

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


app = typer.Typer(help="Line item management (invoice/contract/opportunity items)")


@app.command("add")
def add_line_item(
    parent_type: str = typer.Option(..., "--parent-type", help="Parent entity type (invoice, contract, opportunity, etc.)"),
    parent_id: str = typer.Option(..., "--parent-id", help="Parent entity ID or identifier"),
    unit_price: float = typer.Option(..., "--unit-price", help="Unit price"),
    product: Optional[str] = typer.Option(None, "--product", help="Product slug"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    quantity: Optional[float] = typer.Option(None, "--quantity", "-q", help="Quantity (default 1)"),
    discount: Optional[float] = typer.Option(None, "--discount", help="Discount amount or percentage"),
):
    """Add a line item to a parent entity."""
    client = _require_client()
    data = client.create(
        "line-items",
        parent_type=parent_type,
        parent_id=parent_id,
        unit_price=unit_price,
        product=product,
        description=description,
        quantity=quantity,
        discount=discount,
    )

    emit(data)


@app.command("list")
def list_line_items(
    parent_type: str = typer.Option(..., "--parent-type", help="Parent entity type"),
    parent_id: str = typer.Option(..., "--parent-id", help="Parent entity ID or identifier"),
    pretty: bool = typer.Option(False, "--pretty", "-p", help="Rich table output"),
):
    """List line items for a parent entity."""
    client = _require_client()
    data = client.list("line-items", parent_type=parent_type, parent_id=parent_id)

    emit(
        data,
        pretty=pretty,
        columns=["id", "product", "description", "quantity", "unit_price", "discount", "total"],
        title="Line Items",
    )


@app.command("remove")
def remove_line_item(
    item_id: int = typer.Argument(..., help="Line item ID"),
):
    """Remove a line item by ID."""
    client = _require_client()
    client._request("DELETE", f"line-items/{item_id}/")
    print(f"Line item {item_id} removed.")
