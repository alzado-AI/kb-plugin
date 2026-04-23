"""kb meeting — CRUD for meetings."""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit

from ._crud import register_delete, register_update

app = typer.Typer(help="Meeting management")


register_delete(app, "meetings", label="meeting")
register_update(app, "meetings", label="meeting")

def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required. Set it to the Django backend URL.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_meetings(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    since: Optional[str] = typer.Option(None, "--since", help="ISO date (YYYY-MM-DD)"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List meetings with optional filters."""
    client = _require_client()
    data = client.list("meetings", module=module, since=since)

    emit(
        data,
        pretty=pretty,
        columns=["id", "fecha", "title", "canal", "module", "attendees"],
        title="Meetings",
    )


@app.command("show")
def show_meeting(
    meeting_id: int = typer.Argument(..., help="Meeting ID"),
    full: bool = typer.Option(False, "--full", help="Include raw content"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a meeting by ID."""
    client = _require_client()
    data = client.show("meetings", meeting_id, full="true" if full else None)
    if not data or "error" in data:
        emit(data or {"error": f"Meeting {meeting_id} not found"})
        raise typer.Exit(1)

    emit(data, pretty=pretty, title=f"Meeting: {data.get('title', meeting_id)}")


@app.command("create")
def create_meeting(
    title: str = typer.Argument(..., help="Meeting title"),
    fecha: str = typer.Option(..., "--fecha", "-f", help="Date (YYYY-MM-DD)"),
    canal: Optional[str] = typer.Option(None, "--canal", "-c"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    summary: Optional[str] = typer.Option(None, "--summary", "-s"),
    raw_content: Optional[str] = typer.Option(None, "--raw-content"),
):
    """Create a new meeting."""
    client = _require_client()
    data = client.create(
        "meetings",
        title=title,
        fecha=fecha,
        canal=canal,
        module=module,
        summary=summary,
        raw_content=raw_content,
    )

    emit(data)


@app.command("add-attendee")
def add_attendee(
    meeting_id: int = typer.Argument(..., help="Meeting ID"),
    email: str = typer.Argument(..., help="Person email"),
):
    """Add an attendee to a meeting."""
    client = _require_client()
    data = client.action("meetings", meeting_id, "add-attendee", email=email)
    if data and "error" in data:
        emit(data)
        raise typer.Exit(1)
    emit(data or {"status": "added", "meeting_id": meeting_id, "email": email})


@app.command("add-decision")
def add_decision(
    meeting_id: int = typer.Argument(..., help="Meeting ID"),
    text: str = typer.Argument(..., help="Decision text"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    program: Optional[str] = typer.Option(None, "--program", "-t", help="Program slug"),
    project: Optional[str] = typer.Option(None, "--project", help="Project slug"),
    need_slug: Optional[str] = typer.Option(None, "--need", "-j", help="Need slug"),
):
    """Add a decision to a meeting."""
    client = _require_client()
    kwargs = dict(text=text, module=module, program=program, project=project, need=need_slug)
    # Remove None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    data = client.action("meetings", meeting_id, "add-decision", **kwargs)
    if data and "error" in data:
        emit(data)
        raise typer.Exit(1)
    emit(data)


@app.command("search")
def search_meetings(
    keyword: str = typer.Argument(..., help="Search keyword"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Search meetings by keyword in title or summary."""
    client = _require_client()
    data = client.list("meetings", search=keyword)

    emit(
        data,
        pretty=pretty,
        columns=["id", "fecha", "title", "canal", "module"],
        title=f"Meetings matching '{keyword}'",
    )
