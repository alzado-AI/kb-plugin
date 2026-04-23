"""kb opportunity — CRUD for sales opportunities."""

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

app = typer.Typer(help="Opportunity management (sales pipeline)")


register_delete(app, "opportunities", label="opportunity")

@app.command("list")
def list_opportunities(
    stage: Optional[str] = typer.Option(None, "--stage", "-s", help="Filter by stage"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Filter by company name"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Owner email"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List opportunities with optional filters."""
    client = _require_client()
    data = client.list("opportunities", stage=stage, company=company, owner=owner)

    emit(
        data,
        pretty=pretty,
        columns=["slug", "title", "stage", "company", "expected_revenue", "probability", "close_date", "owner"],
        title="Opportunities",
    )


@app.command("show")
def show_opportunity(
    slug: str = typer.Argument(..., help="Opportunity slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show an opportunity by slug."""
    client = _require_client()
    data = client.show("opportunities", slug)

    emit(data, pretty=pretty, title=f"Opportunity: {slug}")


@app.command("create")
def create_opportunity(
    slug: str = typer.Argument(..., help="Opportunity slug (kebab-case)"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    company_name: Optional[str] = typer.Option(None, "--company", "-c", help="Company name"),
    owner_email: Optional[str] = typer.Option(None, "--owner", "-o", help="Owner person email"),
    stage: str = typer.Option("prospecting", "--stage", "-s"),
    expected_revenue: Optional[str] = typer.Option(None, "--revenue", help="Expected revenue"),
    close_date: Optional[str] = typer.Option(None, "--close-date", help="Expected close date (YYYY-MM-DD)"),
    probability: Optional[int] = typer.Option(None, "--probability", help="Win probability (0-100)"),
    currency: Optional[str] = typer.Option(None, "--currency", help="Currency code (default CLP)"),
):
    """Create a new opportunity."""
    client = _require_client()
    payload = dict(
        slug=slug,
        title=title or slug.replace("-", " ").title(),
        stage=stage,
        estado=stage,  # keep backward compat
    )
    if company_name:
        payload["company"] = company_name
    if owner_email:
        payload["owner"] = owner_email
    if expected_revenue:
        payload["expected_revenue"] = expected_revenue
    if close_date:
        payload["close_date"] = close_date
    if probability is not None:
        payload["probability"] = probability
    if currency:
        payload["currency"] = currency
    data = client.create("opportunities", **payload)

    emit(data)


@app.command("update")
def update_opportunity(
    slug: str = typer.Argument(..., help="Opportunity slug"),
    stage: Optional[str] = typer.Option(None, "--stage", "-s"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    probability: Optional[int] = typer.Option(None, "--probability"),
    expected_revenue: Optional[str] = typer.Option(None, "--revenue"),
    close_date: Optional[str] = typer.Option(None, "--close-date"),
    closed_at: Optional[str] = typer.Option(None, "--closed-at", help="Actual close datetime"),
    lost_reason: Optional[str] = typer.Option(None, "--lost-reason"),
    currency: Optional[str] = typer.Option(None, "--currency"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    external_source: Optional[str] = typer.Option(None, "--external-source"),
):
    """Update an opportunity."""
    client = _require_client()
    updates = {}
    if stage is not None:
        updates["stage"] = stage
        updates["estado"] = stage  # keep backward compat
    if title is not None:
        updates["title"] = title
    if probability is not None:
        updates["probability"] = probability
    if expected_revenue is not None:
        updates["expected_revenue"] = expected_revenue
    if close_date is not None:
        updates["close_date"] = close_date
    if closed_at is not None:
        updates["closed_at"] = closed_at
    if lost_reason is not None:
        updates["lost_reason"] = lost_reason
    if currency is not None:
        updates["currency"] = currency
    if external_id is not None:
        updates["external_id"] = external_id
    if external_source is not None:
        updates["external_source"] = external_source
    data = client.update("opportunities", slug, **updates)

    emit(data)


@app.command("history")
def opportunity_history(
    slug: str = typer.Argument(..., help="Opportunity slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show stage transition history for an opportunity."""
    client = _require_client()
    # First get opportunity to get its ID
    opp = client.show("opportunities", slug)
    opp_id = opp.get("id")
    if not opp_id:
        print(f"Opportunity '{slug}' not found.")
        raise SystemExit(1)

    # Query EstadoHistorial via the generic query endpoint
    data = client.list(
        "estado-historial",
        parent_type="opportunity",
        parent_id=opp_id,
    )

    emit(
        data,
        pretty=pretty,
        columns=["fecha", "texto"],
        title=f"History: {slug}",
    )
