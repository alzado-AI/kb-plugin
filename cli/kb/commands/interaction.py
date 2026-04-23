"""kb interaction — CRUD for interactions (calls, emails, meetings with clients)."""

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

app = typer.Typer(help="Interaction management (client touchpoints)")


register_delete(app, "interactions", label="interaction")
register_update(app, "interactions", label="interaction")

@app.command("list")
def list_interactions(
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Filter by company name"),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t", help="Interaction type"),
    since: Optional[str] = typer.Option(None, "--since", help="Since date (YYYY-MM-DD)"),
    pretty: bool = typer.Option(False, "--pretty", "-p", help="Rich table output"),
):
    """List interactions with optional filters."""
    client = _require_client()
    data = client.list("interactions", company=company, tipo=tipo, since=since)

    emit(
        data,
        pretty=pretty,
        columns=["id", "company", "tipo", "direction", "occurred_at", "summary"],
        title="Interactions",
    )


@app.command("create")
def create_interaction(
    company: str = typer.Option(..., "--company", "-c", help="Company name"),
    tipo: str = typer.Option(..., "--tipo", "-t", help="Interaction type"),
    summary: str = typer.Option(..., "--summary", "-s", help="Interaction summary"),
    direction: str = typer.Option(..., "--direction", "-d", help="Direction (inbound/outbound)"),
    occurred_at: str = typer.Option(..., "--occurred-at", help="Date (YYYY-MM-DD)"),
    channel: Optional[str] = typer.Option(None, "--channel", help="Channel (email, phone, chat, etc)"),
    person_email: Optional[str] = typer.Option(None, "--person-email", help="Contact person email"),
    opportunity: Optional[str] = typer.Option(None, "--opportunity", help="Opportunity slug"),
):
    """Create a new interaction."""
    client = _require_client()
    data = client.create(
        "interactions",
        company=company,
        tipo=tipo,
        summary=summary,
        direction=direction,
        occurred_at=occurred_at,
        channel=channel,
        person_email=person_email,
        opportunity=opportunity,
    )

    emit(data)


@app.command("show")
def show_interaction(
    interaction_id: int = typer.Argument(..., help="Interaction ID"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show an interaction by ID."""
    client = _require_client()
    data = client.show("interactions", interaction_id)

    emit(data, pretty=pretty, title=f"Interaction: {interaction_id}")
