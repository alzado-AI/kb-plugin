"""kb status — infrastructure commands."""

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Infrastructure commands")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command()
def status(
    pretty: bool = typer.Option(False, "--pretty", "-p", help="Rich table output"),
):
    """Show database status: connection, table counts, last update."""
    client = _require_client()
    try:
        data = client.health()
    except Exception as exc:
        emit({"connected": False, "error": str(exc)}, pretty=pretty)
        raise typer.Exit(1)

    emit(data, pretty=pretty, title="KB Database Status")
