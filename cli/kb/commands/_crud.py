"""Shared CRUD helpers for `kb` subcommand modules.

These helpers register generic `delete` and `update` subcommands on a
Typer app so every entity CLI has full CRUD without boilerplate
duplication. Call them right after defining `app = typer.Typer(...)` in
each command module.

Example:
    from ._crud import register_delete, register_update
    app = typer.Typer(...)
    register_delete(app, "meetings", label="meeting")
    register_update(app, "meetings", label="meeting")
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer

from ..client import get_client
from ..output import emit


def _client_or_die():
    client = get_client()
    if not client:
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


def _parse_json(value: Optional[str], label: str):
    """Parse an optional JSON string (e.g. from a Typer option).

    Returns None if value is empty. Exits with code 1 on malformed JSON.
    """
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        print(f"{label} must be valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(1)


def register_delete(
    app: typer.Typer,
    entity: str,
    *,
    label: Optional[str] = None,
    lookup_help: str = "ID or slug",
):
    """Register a generic `delete` command on the given Typer app.

    The command reads an identifier (string; works for both integer PK and
    slug), asks for confirmation unless `--force`, and calls the KB REST
    DELETE endpoint.
    """
    ent_label = label or entity.rstrip("s")

    def _delete(
        identifier: str = typer.Argument(..., help=lookup_help),
        force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    ):
        if not force:
            typer.confirm(
                f"Delete {ent_label} '{identifier}'? This cannot be undone.",
                abort=True,
            )
        client = _client_or_die()
        data = client.delete(entity, identifier)
        if isinstance(data, dict) and data.get("error"):
            emit(data)
            raise typer.Exit(1)
        emit({"ok": True, "deleted": identifier, "entity": ent_label})

    _delete.__doc__ = f"Delete a {ent_label} by ID or slug."
    app.command("delete")(_delete)


def register_update(
    app: typer.Typer,
    entity: str,
    *,
    label: Optional[str] = None,
):
    """Register a generic `update` command that takes arbitrary field=value
    updates via repeatable --set flags.

    Example:
        kb meeting update 42 --set title="Kickoff" --set fecha=2026-04-09
    """
    ent_label = label or entity.rstrip("s")

    def _update(
        identifier: str = typer.Argument(..., help="ID or slug"),
        set_fields: list[str] = typer.Option(
            None, "--set", "-s",
            help="key=value field to update (repeatable). Example: --set title='New title'",
        ),
    ):
        if not set_fields:
            print(
                "Nothing to update. Pass at least one --set key=value.",
                file=sys.stderr,
            )
            raise typer.Exit(1)
        payload: dict = {}
        for item in set_fields:
            if "=" not in item:
                print(f"Ignoring malformed --set value (expected key=value): {item}",
                      file=sys.stderr)
                continue
            k, v = item.split("=", 1)
            payload[k.strip()] = v.strip()
        if not payload:
            raise typer.Exit(1)
        client = _client_or_die()
        data = client.update(entity, identifier, **payload)
        emit(data)

    _update.__doc__ = (
        f"Update a {ent_label}. Pass one or more --set key=value flags."
    )
    app.command("update")(_update)
