"""kb question — CRUD for open questions."""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit

from ._crud import register_delete, register_update

app = typer.Typer(help="Question management")


register_delete(app, "questions", label="question")
register_update(app, "questions", label="question")

def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required. Set it to the Django backend URL.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_questions(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pending: bool = typer.Option(False, "--pending", help="Only open questions"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Filter by parent entity type (program, project, need, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Filter by parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (alternative to --parent-id)"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List questions with optional filters."""
    client = _require_client()
    data = client.list(
        "questions",
        module=module,
        pending="true" if pending else None,
        category=category,
        parent_type=parent_type,
        parent_slug=parent_slug,
        parent_id=parent_id,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "text", "category", "module", "estado"],
        title="Questions",
    )


@app.command("show")
def show_question(
    question_id: int = typer.Argument(..., help="Question ID"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a question by ID."""
    client = _require_client()
    data = client.show("questions", question_id)

    emit(data, pretty=pretty, title=f"Question #{question_id}")


@app.command("create")
def create_question(
    text: str = typer.Argument(..., help="Question text"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    context: Optional[str] = typer.Option(None, "--context"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="Parent entity type (program, project, need, etc.)"),
    parent_id: Optional[int] = typer.Option(None, "--parent-id", help="Parent entity ID"),
    parent_slug: Optional[str] = typer.Option(None, "--parent-slug", help="Parent entity slug (alternative to --parent-id)"),
):
    """Create a new question."""
    client = _require_client()
    data = client.create(
        "questions",
        text=text,
        module=module,
        category=category,
        context=context,
        parent_type=parent_type,
        parent_id=parent_id,
        parent_slug=parent_slug,
    )

    emit(data)


@app.command("answer")
def answer_question(
    question_id: int = typer.Argument(..., help="Question ID"),
    text: str = typer.Argument(..., help="Answer text"),
):
    """Answer a question and mark it as resolved."""
    client = _require_client()
    data = client.update("questions", question_id, answer=text, estado="respondida")

    emit(data)
