"""kb notification — notification center commands."""

from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Notification center")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_notifications(
    unread: bool = typer.Option(False, "--unread", "-u", help="Only unread"),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    with_body: bool = typer.Option(
        False, "--with-body",
        help="Include notification `body`. Default excludes it — "
             "use `kb notification show ID`.",
    ),
):
    """List notifications."""
    client = _require_client()
    kwargs = dict(unread="true" if unread else None, tipo=tipo)
    if with_body:
        kwargs["with_body"] = 1
    data = client.list("notifications", **kwargs)

    if json_output:
        import json
        print(json.dumps(data, default=str))
        return

    emit(
        data,
        pretty=pretty,
        columns=["id", "title", "tipo", "read", "created_at"],
        title="Notifications",
    )


@app.command("show")
def show_notification(
    notification_id: int = typer.Argument(..., help="Notification ID"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show notification details."""
    client = _require_client()
    data = client.show("notifications", notification_id)

    emit(data, pretty=pretty, title=f"Notification #{notification_id}")


@app.command("mark-read")
def mark_read(
    notification_id: int = typer.Argument(..., help="Notification ID"),
):
    """Mark a notification as read."""
    client = _require_client()
    data = client.action("notifications", notification_id, "mark-read")

    emit(data)


@app.command("mark-all-read")
def mark_all_read():
    """Mark all notifications as read."""
    client = _require_client()
    data = client.action_no_id("notifications", "mark-all-read")

    emit(data)


@app.command("count")
def unread_count():
    """Show count of unread notifications."""
    client = _require_client()
    data = client.action_no_id("notifications", "count")

    count = data.get("unread", 0) if isinstance(data, dict) else 0
    print(f"Unread: {count}")
