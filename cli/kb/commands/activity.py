"""kb activity — CRUD for the Activity registry.

Activities are the Temporal-inspired primitive that pipeline steps
invoke. Each Activity declares its kind (script / agent / kb / provider),
code_ref, credentials, schemas, and determinism flag. Steps reference
them by (slug, version).

See ``backend/apps/workflow/README.md`` for the full model.
"""

import json as _json
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


app = typer.Typer(help="Activity registry (pipeline primitives)")


def _parse_json(raw: Optional[str], label: str):
    if raw is None:
        return None
    try:
        return _json.loads(raw)
    except _json.JSONDecodeError as exc:
        typer.echo(f"Error: --{label.replace('_', '-')} is not valid JSON: {exc}")
        raise typer.Exit(1)


@app.command("list")
def list_activities(
    slug: Optional[str] = typer.Option(None, "--slug", help="Filter by slug"),
    kind: Optional[str] = typer.Option(None, "--kind", help="script | agent | kb | provider"),
    deterministic: Optional[bool] = typer.Option(None, "--deterministic/--non-deterministic", help="Filter by determinism"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List registered activities."""
    client = _require_client()
    params = {}
    if slug:
        params["slug"] = slug
    if kind:
        params["kind"] = kind
    if deterministic is not None:
        params["deterministic"] = "true" if deterministic else "false"
    data = client.list("activities", **params)
    emit(
        data, pretty=pretty,
        columns=["id", "slug", "version", "kind", "deterministic", "name"],
        title="Activities",
    )


@app.command("show")
def show_activity(
    slug: str = typer.Argument(..., help="Activity slug"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Specific version (default: latest)"),
    pretty: bool = typer.Option(True, "--pretty/--no-pretty"),
):
    """Show an activity's full definition."""
    client = _require_client()
    params = {"slug": slug}
    if version is not None:
        params["version"] = version
    matches = client.list("activities", **params)
    if not matches:
        typer.echo(f"No activity found for slug='{slug}'" + (f" version={version}" if version else ""))
        raise typer.Exit(1)
    # Pick latest version when unspecified (queryset orders by -version)
    data = matches[0]
    if pretty:
        typer.echo(f"\n  Activity: {data['slug']}@v{data['version']} ({data['kind']})")
        typer.echo(f"  Name:     {data.get('name', '?')}")
        typer.echo(f"  Deterministic: {data.get('deterministic')}   Idempotent: {data.get('idempotent')}")
        typer.echo(f"  Timeout: {data.get('default_timeout_seconds')}s")
        if data.get("description"):
            typer.echo(f"  Desc:     {data['description']}")
        typer.echo(f"  code_ref:\n    {_json.dumps(data.get('code_ref') or {}, indent=2)}")
        if data.get("credentials_required"):
            typer.echo(f"  credentials_required:\n    {_json.dumps(data['credentials_required'], indent=2)}")
        if data.get("input_schema"):
            typer.echo(f"  input_schema:\n    {_json.dumps(data['input_schema'], indent=2)}")
        if data.get("output_schema"):
            typer.echo(f"  output_schema:\n    {_json.dumps(data['output_schema'], indent=2)}")
        typer.echo()
    else:
        emit(data, pretty=False)


@app.command("versions")
def list_versions(
    slug: str = typer.Argument(..., help="Activity slug"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List all versions of an activity."""
    client = _require_client()
    data = client.list("activities", slug=slug)
    emit(
        data, pretty=pretty,
        columns=["id", "version", "kind", "deterministic", "name", "updated_at"],
        title=f"Versions of {slug}",
    )


@app.command("create")
def create_activity(
    slug: str = typer.Argument(..., help="Activity slug (kebab-case; prefix with kind for clarity, e.g. script.foo)"),
    name: str = typer.Option(..., "--name", "-n", help="Display name"),
    kind: str = typer.Option(..., "--kind", "-k", help="script | agent | kb | provider"),
    code_ref: str = typer.Option(..., "--code-ref", help='JSON. kind=script: {"command":"..."} OR {"script_slug":"..."}. kind=agent: {"agent_slug":"..."}.'),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    input_schema: Optional[str] = typer.Option(None, "--input-schema", help="JSON Schema for inputs"),
    output_schema: Optional[str] = typer.Option(None, "--output-schema", help="JSON Schema for outputs"),
    credentials: Optional[str] = typer.Option(None, "--credentials", help='JSON: [{"type":"kb-jwt","as":"owner"}]'),
    deterministic: bool = typer.Option(True, "--deterministic/--non-deterministic", help="Blocks use in workflow-mode pipelines when False"),
    idempotent: bool = typer.Option(False, "--idempotent/--non-idempotent"),
    timeout: int = typer.Option(120, "--default-timeout-seconds", help="Default timeout in seconds"),
    version: int = typer.Option(1, "--version", "-v", help="Version number (bump manually for edits)"),
):
    """Create a new activity version.

    Examples:
      kb activity create script.kb-list --kind script \\
        --name "KB list" \\
        --code-ref '{"command":"kb \"$SCRIPT_VAR_ENTITY\" list $SCRIPT_VAR_ARGS","interpreter":"bash"}' \\
        --deterministic

      kb activity create agent.triage --kind agent \\
        --name "Triage agent" \\
        --code-ref '{"agent_slug":"feedback-triager"}' \\
        --non-deterministic \\
        --credentials '[{"type":"kb-jwt","as":"owner"}]'
    """
    client = _require_client()
    if kind not in ("script", "agent", "kb", "provider"):
        typer.echo(f"Error: --kind must be one of script|agent|kb|provider, got '{kind}'")
        raise typer.Exit(1)

    payload = {
        "slug": slug,
        "version": version,
        "name": name,
        "kind": kind,
        "code_ref": _parse_json(code_ref, "code_ref"),
        "deterministic": deterministic,
        "idempotent": idempotent,
        "default_timeout_seconds": timeout,
    }
    if description:
        payload["description"] = description
    if input_schema is not None:
        payload["input_schema"] = _parse_json(input_schema, "input_schema")
    if output_schema is not None:
        payload["output_schema"] = _parse_json(output_schema, "output_schema")
    if credentials is not None:
        payload["credentials_required"] = _parse_json(credentials, "credentials")

    data = client.create("activities", **payload)
    typer.echo(f"Created {data['slug']}@v{data['version']} ({data['kind']})")
    emit(data, pretty=False)


def _resolve_activity_id(client, slug_or_id: str, version: int | None = None) -> int:
    """Resolve a slug (optionally with version) to a numeric Activity ID.

    If ``slug_or_id`` parses as int, returns it directly. Otherwise looks
    up the activity by slug (latest version when ``version`` is None).
    """
    try:
        return int(slug_or_id)
    except ValueError:
        pass
    params = {"slug": slug_or_id}
    if version is not None:
        params["version"] = version
    matches = client.list("activities", **params)
    if not matches:
        typer.echo(
            f"No activity found for slug='{slug_or_id}'"
            + (f" version={version}" if version else ""),
        )
        raise typer.Exit(1)
    return matches[0]["id"]


@app.command("update")
def update_activity(
    slug_or_id: str = typer.Argument(..., help="Activity slug (e.g. script.kb-list) or numeric ID"),
    name: Optional[str] = typer.Option(None, "--name"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    code_ref: Optional[str] = typer.Option(None, "--code-ref"),
    input_schema: Optional[str] = typer.Option(None, "--input-schema"),
    output_schema: Optional[str] = typer.Option(None, "--output-schema"),
    credentials: Optional[str] = typer.Option(None, "--credentials"),
    deterministic: Optional[bool] = typer.Option(None, "--deterministic/--non-deterministic"),
    idempotent: Optional[bool] = typer.Option(None, "--idempotent/--non-idempotent"),
    timeout: Optional[int] = typer.Option(None, "--default-timeout-seconds"),
):
    """Update an activity in place (edits current row; does not bump version).

    To create a new version instead, use `kb activity create --slug <slug> --version N+1`.
    """
    client = _require_client()
    payload: dict = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if deterministic is not None:
        payload["deterministic"] = deterministic
    if idempotent is not None:
        payload["idempotent"] = idempotent
    if timeout is not None:
        payload["default_timeout_seconds"] = timeout
    for raw_name, raw in (
        ("code_ref", code_ref),
        ("input_schema", input_schema),
        ("output_schema", output_schema),
    ):
        if raw is not None:
            payload[raw_name] = _parse_json(raw, raw_name)
    if credentials is not None:
        payload["credentials_required"] = _parse_json(credentials, "credentials")
    if not payload:
        typer.echo("Error: provide at least one field to update")
        raise typer.Exit(1)
    activity_id = _resolve_activity_id(client, slug_or_id)
    data = client.update("activities", activity_id, **payload)
    typer.echo(f"Updated activity #{activity_id}: {data['slug']}@v{data['version']}")
    emit(data, pretty=False)


@app.command("delete")
def delete_activity(
    slug_or_id: str = typer.Argument(..., help="Activity slug or numeric ID"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Specific version when slug has multiple"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete an activity version.

    Warning: fails if any PipelineStep still references this (slug, version).
    """
    client = _require_client()
    activity_id = _resolve_activity_id(client, slug_or_id, version=version)
    if not confirm:
        if not typer.confirm(f"Delete activity #{activity_id}?"):
            typer.echo("Cancelled.")
            raise typer.Exit()
    client.delete("activities", activity_id)
    typer.echo(f"Deleted activity #{activity_id}")
