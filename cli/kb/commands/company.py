"""kb company — CRUD for companies (clients, partners, competitors)."""

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

app = typer.Typer(help="Company management")


register_delete(app, "companies", label="company")

@app.command("list")
def list_companies(
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t"),
    segment: Optional[str] = typer.Option(None, "--segment"),
    lifecycle: Optional[str] = typer.Option(None, "--lifecycle"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List companies with optional filters."""
    client = _require_client()
    data = client.list(
        "companies", tipo=tipo, segment=segment, lifecycle_stage=lifecycle,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "name", "tipo", "segment", "lifecycle_stage", "estado"],
        title="Companies",
    )


@app.command("show")
def show_company(
    name: str = typer.Argument(..., help="Company name (partial match)"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a company by name."""
    client = _require_client()
    data = client.show("companies", name)

    emit(data, pretty=pretty, title=f"Company: {name}")


@app.command("create")
def create_company(
    name: str = typer.Argument(..., help="Company name"),
    tipo: str = typer.Option(..., "--tipo", "-t", help="Company type (use kb entity-state list --entity company --field tipo for valid values)"),
    contact_name: Optional[str] = typer.Option(None, "--contact-name"),
    contact_email: Optional[str] = typer.Option(None, "--contact-email"),
    estado: Optional[str] = typer.Option(None, "--estado"),
    context: Optional[str] = typer.Option(None, "--context"),
    segment: Optional[str] = typer.Option(None, "--segment", help="Company segment (use kb entity-state list --entity company --field segment)"),
    industry: Optional[str] = typer.Option(None, "--industry"),
    lifecycle: Optional[str] = typer.Option(None, "--lifecycle", help="Lifecycle stage (use kb entity-state list --entity company --field lifecycle)"),
    owner: Optional[str] = typer.Option(None, "--owner", help="Owner email"),
    annual_revenue: Optional[float] = typer.Option(None, "--annual-revenue"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    external_source: Optional[str] = typer.Option(None, "--external-source"),
):
    """Create a new company."""
    client = _require_client()
    data = client.create(
        "companies",
        name=name,
        tipo=tipo,
        contact_name=contact_name,
        contact_email=contact_email,
        estado=estado,
        context=context,
        segment=segment,
        industry=industry,
        lifecycle_stage=lifecycle,
        owner=owner,
        annual_revenue_estimate=annual_revenue,
        external_id=external_id,
        external_source=external_source,
    )

    emit(data)


@app.command("update")
def update_company(
    name: str = typer.Argument(..., help="Company name (partial match)"),
    estado: Optional[str] = typer.Option(None, "--estado"),
    context: Optional[str] = typer.Option(None, "--context"),
    contact_name: Optional[str] = typer.Option(None, "--contact-name"),
    contact_email: Optional[str] = typer.Option(None, "--contact-email"),
    segment: Optional[str] = typer.Option(None, "--segment"),
    industry: Optional[str] = typer.Option(None, "--industry"),
    lifecycle: Optional[str] = typer.Option(None, "--lifecycle"),
    owner: Optional[str] = typer.Option(None, "--owner", help="Owner email"),
    annual_revenue: Optional[float] = typer.Option(None, "--annual-revenue"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    external_source: Optional[str] = typer.Option(None, "--external-source"),
):
    """Update a company."""
    client = _require_client()
    data = client.update(
        "companies", name,
        estado=estado,
        context=context,
        contact_name=contact_name,
        contact_email=contact_email,
        segment=segment,
        industry=industry,
        lifecycle_stage=lifecycle,
        owner=owner,
        annual_revenue_estimate=annual_revenue,
        external_id=external_id,
        external_source=external_source,
    )

    emit(data)
