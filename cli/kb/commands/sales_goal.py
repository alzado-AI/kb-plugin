"""kb sales-goal — CRUD for commercial targets and quotas."""

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

app = typer.Typer(help="Sales goal management (targets and quotas)")


register_delete(app, "sales-goals", label="sales goal")

@app.command("list")
def list_goals(
    periodo: Optional[str] = typer.Option(None, "--periodo", help="Filter by period"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Owner email"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List sales goals."""
    client = _require_client()
    data = client.list("sales-goals", periodo=periodo, module=module, owner=owner)

    emit(
        data,
        pretty=pretty,
        columns=["name", "metric", "target", "actual", "periodo", "owner", "module"],
        title="Sales Goals",
    )


@app.command("show")
def show_goal(
    goal_id: int = typer.Argument(..., help="Sales goal ID"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a sales goal by ID."""
    client = _require_client()
    data = client.show("sales-goals", goal_id)

    emit(data, pretty=pretty, title=f"Sales Goal #{goal_id}")


@app.command("create")
def create_goal(
    name: str = typer.Argument(..., help="Goal name"),
    periodo: str = typer.Option(..., "--periodo", help="Period (e.g. 2026-Q1, 2026-H1)"),
    metric: Optional[str] = typer.Option(None, "--metric", help="Metric name (e.g. revenue, deals_closed)"),
    target: Optional[str] = typer.Option(None, "--target", help="Target value"),
    owner_email: Optional[str] = typer.Option(None, "--owner", "-o"),
    module_slug: Optional[str] = typer.Option(None, "--module", "-m"),
):
    """Create a new sales goal."""
    client = _require_client()
    payload = dict(name=name, periodo=periodo)
    if metric:
        payload["metric"] = metric
    if target:
        payload["target"] = target
    if owner_email:
        payload["owner"] = owner_email
    if module_slug:
        payload["module"] = module_slug
    data = client.create("sales-goals", **payload)

    emit(data)


@app.command("update")
def update_goal(
    goal_id: int = typer.Argument(..., help="Sales goal ID"),
    target: Optional[str] = typer.Option(None, "--target"),
    actual: Optional[str] = typer.Option(None, "--actual", help="Actual/current value"),
    metric: Optional[str] = typer.Option(None, "--metric"),
    name: Optional[str] = typer.Option(None, "--name"),
):
    """Update a sales goal (typically to set actual progress)."""
    client = _require_client()
    updates = {}
    if target is not None:
        updates["target"] = target
    if actual is not None:
        updates["actual"] = actual
    if metric is not None:
        updates["metric"] = metric
    if name is not None:
        updates["name"] = name
    data = client.update("sales-goals", goal_id, **updates)

    emit(data)


@app.command("link")
def link_opportunity(
    goal_id: int = typer.Argument(..., help="Sales goal ID"),
    opportunity: str = typer.Option(..., "--opportunity", help="Opportunity slug"),
    contribution: Optional[str] = typer.Option(None, "--contribution", help="Contribution amount"),
):
    """Link an opportunity to a sales goal."""
    client = _require_client()
    payload = {"opportunity": opportunity}
    if contribution:
        payload["contribution"] = contribution
    data = client._request(
        "POST", f"sales-goals/{goal_id}/link-opportunity/", json=payload,
    )

    emit(data)


@app.command("unlink")
def unlink_opportunity(
    goal_id: int = typer.Argument(..., help="Sales goal ID"),
    opportunity: str = typer.Option(..., "--opportunity", help="Opportunity slug"),
):
    """Unlink an opportunity from a sales goal."""
    client = _require_client()
    data = client._request(
        "DELETE", f"sales-goals/{goal_id}/link-opportunity/{opportunity}/",
    )

    emit(data)
