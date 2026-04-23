"""kb product — CRUD for products (catalog items)."""

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

app = typer.Typer(help="Product catalog management")


register_delete(app, "products", label="product")

@app.command("list")
def list_products(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    pretty: bool = typer.Option(False, "--pretty", "-p", help="Rich table output"),
):
    """List products with optional filters."""
    client = _require_client()
    data = client.list("products", category=category)

    emit(
        data,
        pretty=pretty,
        columns=["slug", "name", "category", "unit_price", "currency", "estado"],
        title="Products",
    )


@app.command("create")
def create_product(
    slug: str = typer.Argument(..., help="Product slug (kebab-case)"),
    name: str = typer.Option(..., "--name", "-n", help="Product name"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    unit_price: Optional[float] = typer.Option(None, "--unit-price", help="Unit price"),
    currency: Optional[str] = typer.Option(None, "--currency", help="Currency code (e.g. USD, CLP)"),
):
    """Create a new product."""
    client = _require_client()
    data = client.create(
        "products",
        slug=slug,
        name=name,
        description=description,
        category=category,
        unit_price=unit_price,
        currency=currency,
    )

    emit(data)


@app.command("update")
def update_product(
    slug: str = typer.Argument(..., help="Product slug"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    unit_price: Optional[float] = typer.Option(None, "--unit-price"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
):
    """Update a product."""
    client = _require_client()
    updates = {}
    if name is not None:
        updates["name"] = name
    if unit_price is not None:
        updates["unit_price"] = unit_price
    if estado is not None:
        updates["estado"] = estado
    if category is not None:
        updates["category"] = category
    data = client.update("products", slug, **updates)

    emit(data)


@app.command("show")
def show_product(
    slug: str = typer.Argument(..., help="Product slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a product by slug."""
    client = _require_client()
    data = client.show("products", slug)

    emit(data, pretty=pretty, title=f"Product: {slug}")
