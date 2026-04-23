"""kb issue — CRUD for issues (bugs, feature requests, improvements)."""

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


app = typer.Typer(help="Issue management")


@app.command("list")
def list_issues(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="Assignee email"),
    program: Optional[str] = typer.Option(None, "--program", "-t", help="Program slug"),
    project: Optional[str] = typer.Option(None, "--project", help="Project slug"),
    tipo: Optional[str] = typer.Option(None, "--tipo", help="bug|feature-request|mejora"),
    need: Optional[str] = typer.Option(None, "--need", "-j", help="Filter by need slug"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List issues with optional filters."""
    client = _require_client()
    data = client.list("issues", module=module, estado=estado, assignee=assignee,
                       program=program, project=project, tipo=tipo, need=need)

    emit(
        data,
        pretty=pretty,
        columns=["id", "title", "tipo", "estado", "priority", "module", "assignee", "program"],
        title="Issues",
    )


@app.command("create")
def create_issue(
    title: str = typer.Argument(..., help="Issue title"),
    tipo: str = typer.Option("bug", "--tipo", help="bug|feature-request|mejora"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    reporter: Optional[str] = typer.Option(None, "--reporter", help="Reporter email"),
    assignee_email: Optional[str] = typer.Option(None, "--assignee", "-a", help="Assignee email"),
    program_slug: Optional[str] = typer.Option(None, "--program", "-t", help="Program slug"),
    project_slug: Optional[str] = typer.Option(None, "--project", help="Project slug"),
    meeting_id: Optional[int] = typer.Option(None, "--meeting-id", help="Origin meeting ID"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    external_url: Optional[str] = typer.Option(None, "--external-url"),
    external_source: Optional[str] = typer.Option(None, "--external-source"),
    priority: Optional[str] = typer.Option(
        None, "--priority", "-p",
        help="Priority: sin-prioridad|critica|alta|media|baja",
    ),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    need_slug: Optional[str] = typer.Option(None, "--need", "-j", help="Need slug"),
    force: bool = typer.Option(False, "--force", help="Skip duplicate check"),
):
    """Create a new issue."""
    client = _require_client()
    data = client.create(
        "issues", title=title, tipo=tipo, description=description,
        module_slug=module, reporter=reporter, assignee_email=assignee_email,
        program_slug=program_slug, project_slug=project_slug, meeting_id=meeting_id,
        external_id=external_id, external_url=external_url,
        external_source=external_source, priority=priority,
        tags=[t.strip() for t in tags.split(",")] if tags else None,
        need_slug=need_slug, force="true" if force else None,
    )

    emit(data)


@app.command("show")
def show_issue(
    issue_id: int = typer.Argument(..., help="Issue ID"),
):
    """Show issue details."""
    client = _require_client()
    data = client.show("issues", issue_id, full="true")

    emit(data)


@app.command("update")
def update_issue(
    issue_id: int = typer.Argument(..., help="Issue ID"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    assignee_email: Optional[str] = typer.Option(None, "--assignee", "-a"),
    priority: Optional[str] = typer.Option(
        None, "--priority", "-p",
        help="Priority: sin-prioridad|critica|alta|media|baja",
    ),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    external_url: Optional[str] = typer.Option(None, "--external-url"),
    external_source: Optional[str] = typer.Option(None, "--external-source"),
):
    """Update an issue."""
    client = _require_client()
    data = client.update("issues", issue_id, estado=estado, assignee_email=assignee_email,
                         priority=priority, description=description,
                         external_id=external_id, external_url=external_url,
                         external_source=external_source)

    emit(data)


@app.command("resolve")
def resolve_issue(
    issue_id: int = typer.Argument(..., help="Issue ID"),
):
    """Resolve an issue (set estado=resuelto + resolved_at)."""
    client = _require_client()
    data = client.action("issues", issue_id, "resolve")

    emit(data)


@app.command("find")
def find_issue(
    keyword: str = typer.Argument(..., help="Keyword to search"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Find issues by keyword (FTS with ILIKE fallback)."""
    client = _require_client()
    data = client.list("issues", search=keyword, module=module)

    emit(
        data,
        pretty=pretty,
        columns=["id", "title", "tipo", "estado", "priority", "module", "assignee"],
        title=f"Issues matching '{keyword}'",
    )


@app.command("link-external")
def link_external(
    issue_id: int = typer.Argument(..., help="Issue ID"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    external_url: Optional[str] = typer.Option(None, "--external-url"),
    external_source: Optional[str] = typer.Option(None, "--external-source"),
):
    """Link an issue to an external system (Linear, Jira, etc)."""
    client = _require_client()
    data = client.update("issues", issue_id, external_id=external_id,
                         external_url=external_url, external_source=external_source)

    emit(data)


@app.command("cancel")
def cancel_issue(
    issue_id: int = typer.Argument(..., help="Issue ID"),
):
    """Cancel an issue (set estado=cancelado). Use for issues created by mistake or superseded."""
    client = _require_client()
    data = client.update("issues", issue_id, estado="cancelado")

    emit(data)


@app.command("delete")
def delete_issue(
    issue_id: int = typer.Argument(..., help="Issue ID"),
):
    """Hard-delete an issue. Prefer cancel for audit trail."""
    client = _require_client()
    data = client.delete("issues", issue_id)

    emit(data)
