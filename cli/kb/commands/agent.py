"""kb agent — Agent workforce management (list, show, pause, resume, triggers)."""

from pathlib import Path
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

app = typer.Typer(help="Agent workforce management")


register_delete(app, "agents", label="agent")

# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------


@app.command("list")
def list_agents(
    tree: bool = typer.Option(False, "--tree", help="Show org chart tree"),
    role: Optional[str] = typer.Option(None, "--role", "-r"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    pretty: bool = typer.Option(False, "--pretty"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results to show"),
    with_body: bool = typer.Option(
        False, "--with-body",
        help="Include `definition_body` in list results. Default excludes it — "
             "use `kb agent show SLUG` to read a specific definition.",
    ),
):
    """List agents, optionally as org chart tree."""
    client = _require_client()

    if tree:
        data = client.get("agents/org-chart")
        if pretty:
            _print_tree(data)
        else:
            emit(data, pretty=True)
        return

    params = {}
    if role:
        params["role"] = role
    if estado:
        params["estado"] = estado
    if with_body:
        params["with_body"] = 1
    data = client.list("agents", **params)
    if limit and isinstance(data, list):
        data = data[:limit]
    emit(
        data, pretty=pretty,
        columns=["slug", "role", "estado", "total_runs", "last_run_at"],
        title="Agents",
    )


@app.command("show")
def show_agent(
    slug: str = typer.Argument(..., help="Agent slug"),
    pretty: bool = typer.Option(True, "--pretty/--no-pretty"),
):
    """Show agent profile + stats."""
    client = _require_client()
    data = client.get(f"agents/{slug}")
    emit(data, pretty=pretty)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@app.command("pause")
def pause_agent(
    slug: str = typer.Argument(..., help="Agent slug"),
    reason: str = typer.Option("manual", "--reason", "-r"),
):
    """Pause an agent (stops heartbeats and invocations)."""
    client = _require_client()
    data = client.post(f"agents/{slug}/pause", {"reason": reason})
    typer.echo(f"Paused {slug} (reason: {reason})")
    emit(data, pretty=True)


@app.command("resume")
def resume_agent(
    slug: str = typer.Argument(..., help="Agent slug"),
):
    """Resume a paused agent."""
    client = _require_client()
    data = client.post(f"agents/{slug}/resume", {})
    typer.echo(f"Resumed {slug}")
    emit(data, pretty=True)


# ---------------------------------------------------------------------------
# Runs & Costs (read-only views)
# ---------------------------------------------------------------------------


@app.command("runs")
def list_runs(
    agent: Optional[str] = typer.Option(None, "--agent", "-a"),
    status: Optional[str] = typer.Option(None, "--status"),
    pretty: bool = typer.Option(False, "--pretty"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """List recent agent runs."""
    client = _require_client()
    params = {}
    if agent:
        params["agent"] = agent
    if status:
        params["status"] = status
    data = client.list("agent-runs", **params)
    if isinstance(data, list):
        data = data[:limit]
    emit(
        data, pretty=pretty,
        columns=["id", "agent_slug", "invocation_source", "status",
                 "started_at", "finished_at"],
        title="Agent Runs",
    )


@app.command("costs")
def list_costs(
    agent: Optional[str] = typer.Option(None, "--agent", "-a"),
    pretty: bool = typer.Option(False, "--pretty"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """List recent cost events."""
    client = _require_client()
    params = {}
    if agent:
        params["agent"] = agent
    data = client.list("cost-events", **params)
    if isinstance(data, list):
        data = data[:limit]
    emit(
        data, pretty=pretty,
        columns=["id", "agent_slug", "provider", "model", "input_tokens",
                 "output_tokens", "cost_cents", "occurred_at"],
        title="Cost Events",
    )


@app.command("activity")
def list_activity(
    agent: Optional[str] = typer.Option(None, "--agent", "-a"),
    action: Optional[str] = typer.Option(None, "--action"),
    pretty: bool = typer.Option(False, "--pretty"),
    limit: int = typer.Option(30, "--limit", "-n"),
):
    """List activity log entries."""
    client = _require_client()
    params = {}
    if agent:
        params["agent"] = agent
    if action:
        params["action"] = action
    data = client.list("activity-log", **params)
    if isinstance(data, list):
        data = data[:limit]
    emit(
        data, pretty=pretty,
        columns=["created_at", "actor_type", "actor_id", "action",
                 "entity_type", "entity_id"],
        title="Activity Log",
    )


# ---------------------------------------------------------------------------
# Sync definitions from disk to DB
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text. Returns (metadata, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    front = text[3:end].strip()
    body = text[end + 3:].strip()
    meta = {}
    for line in front.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        val = val.strip().strip('"').strip("'")
        meta[key.strip()] = val
    return meta, body


@app.command("sync-definitions")
def sync_definitions(
    path: str = typer.Option(".claude/agents", "--path", "-p", help="Path to agent .md files"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Sync agent definitions from .md files to database."""
    from ..client import APIError as _APIError

    client = _require_client()
    agents_path = Path(path)
    if not agents_path.is_dir():
        typer.echo(f"Directory not found: {path}", err=True)
        raise typer.Exit(1)

    # Scan .md files (skip shared/ subdirectory)
    md_files = [f for f in sorted(agents_path.glob("*.md")) if f.is_file()]
    if not md_files:
        typer.echo(f"No .md files found in {path}")
        return

    # Get existing agents from DB
    existing = {a["slug"]: a for a in client.list("agents")}

    created, updated, skipped, errors = 0, 0, 0, 0

    for md_file in md_files:
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception as e:
            typer.echo(f"  ERROR reading {md_file.name}: {e}", err=True)
            errors += 1
            continue

        meta, _body = _parse_frontmatter(text)
        slug = meta.get("name", md_file.stem)
        description = meta.get("description", "")
        model = meta.get("model", "")

        if slug in existing:
            # Check if update needed
            ex = existing[slug]
            needs_update = False
            payload = {}
            if description and description != ex.get("description", ""):
                payload["description"] = description
                needs_update = True
            if model and model != ex.get("model_preference", ""):
                payload["model_preference"] = model
                needs_update = True

            if needs_update:
                if dry_run:
                    typer.echo(f"  UPDATE {slug} ({', '.join(payload.keys())})")
                else:
                    try:
                        client.update("agents", slug, **payload)
                        typer.echo(f"  updated {slug}")
                    except Exception as e:
                        typer.echo(f"  ERROR updating {slug}: {e}", err=True)
                        errors += 1
                        continue
                updated += 1
            else:
                skipped += 1
        else:
            # Create new agent
            payload = {
                "slug": slug,
                "name": slug.replace("-", " ").title(),
                "role": "utility",
            }
            if description:
                payload["description"] = description
            if model:
                payload["model_preference"] = model

            if dry_run:
                typer.echo(f"  CREATE {slug}")
            else:
                try:
                    client.create("agents", **payload)
                    typer.echo(f"  created {slug}")
                except Exception as e:
                    typer.echo(f"  ERROR creating {slug}: {e}", err=True)
                    errors += 1
                    continue
            created += 1

    # Summary
    action = "Would sync" if dry_run else "Synced"
    typer.echo(f"\n{action}: {created} created, {updated} updated, {skipped} unchanged, {errors} errors")
    typer.echo(f"Scanned {len(md_files)} files, DB has {len(existing)} agents")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_tree(nodes, indent=0):
    """Print org chart tree to terminal."""
    for node in nodes:
        prefix = "  " * indent + ("├── " if indent > 0 else "")
        status = node.get("estado", "?")
        icon = node.get("icon", "")
        runs = node.get("total_runs", 0)
        runs_str = f" [{runs} runs]" if runs > 0 else ""
        typer.echo(f"{prefix}{icon}{node['slug']} ({node.get('role', '?')}) [{status}]{runs_str}")
        children = node.get("direct_reports", [])
        if children:
            _print_tree(children, indent + 1)
