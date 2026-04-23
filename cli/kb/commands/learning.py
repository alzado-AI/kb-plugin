"""kb learning — CRUD for learning resources and insights."""

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

app = typer.Typer(help="Learning resource management")


register_delete(app, "learnings", label="learning")
register_update(app, "learnings", label="learning")

@app.command("list")
def list_learning(
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
    with_body: bool = typer.Option(
        False, "--with-body",
        help="Include full body. Default excludes it — use `kb learning show ID`.",
    ),
):
    """List learning entries with optional type filter."""
    client = _require_client()
    kwargs = {"tipo": tipo}
    if with_body:
        kwargs["with_body"] = 1
    data = client.list("learnings", **kwargs)

    emit(
        data,
        pretty=pretty,
        columns=["id", "tipo", "title", "source"],
        title="Learning",
    )


@app.command("show")
def show_learning(
    learning_id: int = typer.Argument(..., help="Learning ID"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a learning entry by ID."""
    client = _require_client()
    data = client.show("learnings", learning_id)

    if "error" in data:
        emit(data)
        raise typer.Exit(1)
    emit(data, pretty=pretty, title=f"Learning: {data.get('title', learning_id)}")


@app.command("create")
def create_learning(
    title: str = typer.Argument(..., help="Title"),
    tipo: str = typer.Option(..., "--tipo", "-t", help="Type (framework, insight, referente, codebase, feedback)"),
    body: Optional[str] = typer.Option(None, "--body", "-b"),
    source: Optional[str] = typer.Option(None, "--source", "-s"),
    sources: Optional[str] = typer.Option(
        None, "--sources",
        help="Comma-separated list of source URLs (e.g. 'https://a.com,https://b.com'). "
             "Stored as a JSON list for full traceability.",
    ),
):
    """Create a new learning entry."""
    client = _require_client()
    sources_list = [u.strip() for u in sources.split(",") if u.strip()] if sources else []
    data = client.create(
        "learnings",
        title=title,
        tipo=tipo,
        body=body,
        source=source,
        sources=sources_list,
    )

    emit(data)


@app.command("search")
def search_learning(
    keyword: str = typer.Argument(..., help="Search keyword"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Search learning entries by keyword."""
    client = _require_client()
    data = client.list("learnings", search=keyword)

    emit(
        data,
        pretty=pretty,
        columns=["id", "tipo", "title", "source"],
        title=f"Learning matching '{keyword}'",
    )
