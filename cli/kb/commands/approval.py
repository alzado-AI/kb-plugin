"""kb approval — Agent workforce approval management (CPO decision queue)."""

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


app = typer.Typer(help="Agent approval management (CPO decision queue)")


@app.command("list")
def list_approvals(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="pending|approved|rejected"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List approvals, optionally filtered by status or agent."""
    client = _require_client()
    params = {}
    if status:
        params["status"] = status
    if agent:
        params["agent"] = agent
    data = client.list("approvals", **params)
    emit(
        data, pretty=pretty,
        columns=["id", "status", "title", "entity_type", "entity_id", "agent_slug", "created_at"],
        title="Approvals",
    )


@app.command("create")
def create_approval(
    title: str = typer.Argument(..., help="What needs approval"),
    entity_type: str = typer.Option(..., "--entity-type", "-t", help="Entity type (feedback, issue, program, etc.)"),
    entity_id: str = typer.Option(..., "--entity-id", "-i", help="Entity ID"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Full analysis and recommendation"),
    doc_url: Optional[str] = typer.Option(None, "--doc-url", help="Link to relevant document"),
):
    """Create an approval request for the CPO."""
    client = _require_client()
    payload = {
        "title": title,
        "entity_type": entity_type,
        "entity_id": entity_id,
    }
    if description:
        payload["description"] = description
    if doc_url:
        payload["doc_url"] = doc_url
    data = client.create("approvals", **payload)
    emit(data, pretty=True)


@app.command("show")
def show_approval(
    approval_id: int = typer.Argument(..., help="Approval ID"),
    pretty: bool = typer.Option(True, "--pretty/--no-pretty"),
):
    """Show approval details."""
    client = _require_client()
    data = client.get(f"approvals/{approval_id}")
    emit(data, pretty=pretty)


@app.command("approve")
def approve_approval(
    approval_id: int = typer.Argument(..., help="Approval ID"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Optional approval notes"),
):
    """Approve a pending approval request."""
    client = _require_client()
    data = client.action("approvals", approval_id, "approve", notes=notes)
    emit(data)


@app.command("reject")
def reject_approval(
    approval_id: int = typer.Argument(..., help="Approval ID"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="Reason for rejection"),
):
    """Reject a pending approval request."""
    client = _require_client()
    data = client.action("approvals", approval_id, "reject", notes=notes)
    emit(data)
