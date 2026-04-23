"""kb feedback — CRUD + pipeline actions for client feedback."""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit

from ._crud import register_delete

app = typer.Typer(help="Client feedback management")


register_delete(app, "feedback", label="feedback")

def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required. Set it to the Django backend URL.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_feedback(
    estado: Optional[str] = typer.Option(None, "--estado", "-e", help="Filter by estado (comma-separated)"),
    clasificacion: Optional[str] = typer.Option(None, "--clasificacion", "-c"),
    severidad: Optional[str] = typer.Option(None, "--severidad"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    with_body: bool = typer.Option(
        False, "--with-body",
        help="Include heavy fields (raw_message, body, triage_summary, "
             "execution_plan, client_response, duplicates). Default excludes them — "
             "use `kb feedback show ID` for a specific item.",
    ),
):
    """List client feedback with optional filters."""
    client = _require_client()
    kwargs = dict(
        estado=estado,
        clasificacion=clasificacion,
        severidad=severidad,
        module=module,
        limit=limit,
    )
    if with_body:
        kwargs["with_body"] = 1
    data = client.list("feedback", **kwargs)

    if json_output:
        import json
        print(json.dumps(data, default=str))
        return

    emit(
        data,
        pretty=pretty,
        columns=["id", "title", "clasificacion", "severidad", "estado", "module", "client_name"],
        title="Client Feedback",
    )


@app.command("show")
def show_feedback(
    feedback_id: int = typer.Argument(..., help="Feedback ID"),
    full: bool = typer.Option(False, "--full", help="Show all fields including plan"),
    pretty: bool = typer.Option(False, "--pretty"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Show feedback details."""
    client = _require_client()
    data = client.show("feedback", feedback_id)

    if json_output:
        import json
        print(json.dumps(data, default=str))
        return

    if full:
        emit(data, pretty=pretty, title=f"Feedback #{feedback_id}")
    else:
        # Exclude large fields for compact view
        compact = {k: v for k, v in data.items() if k not in ("execution_plan", "triage_summary", "duplicates", "raw_message")}
        emit(compact, pretty=pretty, title=f"Feedback #{feedback_id}")


@app.command("create")
def create_feedback(
    title: str = typer.Argument(..., help="Feedback title"),
    raw_message: str = typer.Option(..., "--raw-message", "-r", help="Original client message"),
    client_name: Optional[str] = typer.Option(None, "--client-name"),
    client_email: Optional[str] = typer.Option(None, "--client-email"),
    client_company: Optional[str] = typer.Option(None, "--client-company", help="Company name"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
):
    """Create a new feedback entry."""
    client = _require_client()
    data = client.create(
        "feedback",
        title=title,
        raw_message=raw_message,
        client_name=client_name,
        client_email=client_email,
        client_company_name=client_company,
        module=module,
        tags=[t.strip() for t in tags.split(",")] if tags else None,
    )

    emit(data)


@app.command("update")
def update_feedback(
    feedback_id: int = typer.Argument(..., help="Feedback ID"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    clasificacion: Optional[str] = typer.Option(None, "--clasificacion", "-c"),
    severidad: Optional[str] = typer.Option(None, "--severidad"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    client_email: Optional[str] = typer.Option(None, "--client-email"),
):
    """Update feedback fields."""
    client = _require_client()
    kwargs = {}
    if title:
        kwargs["title"] = title
    if client_email:
        kwargs["client_email"] = client_email
    if clasificacion:
        kwargs["clasificacion"] = clasificacion
    if severidad:
        kwargs["severidad"] = severidad
    if estado:
        kwargs["estado"] = estado
    if module:
        kwargs["module"] = module
    data = client.update("feedback", feedback_id, **kwargs)

    emit(data)


@app.command("triage")
def triage_feedback(
    feedback_id: int = typer.Argument(..., help="Feedback ID"),
    triage_summary: str = typer.Option(..., "--triage-summary", "-t", help="Triage summary text"),
    clasificacion: str = typer.Option(..., "--clasificacion", "-c"),
    severidad: str = typer.Option(..., "--severidad", "-s"),
    duplicates: Optional[str] = typer.Option(None, "--duplicates", help="JSON array of duplicates"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
):
    """Run triage on feedback (classification + summary)."""
    client = _require_client()
    payload = {
        "triage_summary": triage_summary,
        "clasificacion": clasificacion,
        "severidad": severidad,
    }
    if duplicates:
        import json
        payload["duplicates"] = json.loads(duplicates)
    if module:
        payload["module"] = module
    data = client.action("feedback", feedback_id, "triage", **payload)

    emit(data)


@app.command("plan")
def plan_feedback(
    feedback_id: int = typer.Argument(..., help="Feedback ID"),
    execution_plan: str = typer.Option(..., "--execution-plan", "-p", help="Execution plan text"),
):
    """Store execution plan for feedback."""
    client = _require_client()
    data = client.action("feedback", feedback_id, "plan", execution_plan=execution_plan)

    emit(data)


@app.command("derive")
def derive_feedback(
    feedback_id: int = typer.Argument(..., help="Feedback ID"),
    derived_type: str = typer.Option(..., "--type", "-t", help="Entity type (issue, program, project, todo)"),
    derived_id: int = typer.Option(..., "--id", "-i", help="Entity ID"),
):
    """Link feedback to a derived entity."""
    client = _require_client()
    data = client.action("feedback", feedback_id, "derive", derived_type=derived_type, derived_id=derived_id)

    emit(data)


@app.command("respond")
def respond_feedback(
    feedback_id: int = typer.Argument(..., help="Feedback ID"),
    client_response: str = typer.Option(..., "--client-response", "-r", help="Response text for the client"),
):
    """Store client response for recommendation-type feedback. Creates notification."""
    client = _require_client()
    data = client.action("feedback", feedback_id, "respond", client_response=client_response)

    emit(data)


@app.command("resolve")
def resolve_feedback(
    feedback_id: int = typer.Argument(..., help="Feedback ID"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Resolution note"),
):
    """Mark feedback as resolved."""
    client = _require_client()
    data = client.action("feedback", feedback_id, "resolve", note=note)

    emit(data)


@app.command("find")
def find_feedback(
    keyword: str = typer.Argument(..., help="Keyword to search"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Find feedback by keyword."""
    client = _require_client()
    data = client.list(
        "feedback",
        search=keyword,
        module=module,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "title", "clasificacion", "severidad", "estado", "client_name"],
        title=f"Feedback matching '{keyword}'",
    )
