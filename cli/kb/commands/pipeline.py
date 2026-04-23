"""kb pipeline — Create and manage automated agent pipelines (DAG-based)."""

import json as _json
import os
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


app = typer.Typer(help="Pipeline management (DAG-based automated agent workflows)")


# ---------------------------------------------------------------------------
# Pipeline CRUD
# ---------------------------------------------------------------------------


@app.command("list")
def list_pipelines(
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List pipelines."""
    client = _require_client()
    params = {}
    if status:
        params["status"] = status
    data = client.list("pipelines", **params)
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "trigger_event", "on_failure", "status", "steps_count"],
        title="Pipelines",
    )


@app.command("show")
def show_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
    pretty: bool = typer.Option(True, "--pretty/--no-pretty"),
):
    """Show pipeline with all steps and DAG dependencies."""
    client = _require_client()
    data = client.get(f"pipelines/{slug}")

    if pretty:
        typer.echo(f"\n  Pipeline: {data.get('name', slug)}")
        ttype = data.get('trigger_type', 'event')
        if ttype == 'event':
            typer.echo(f"  Trigger:  {ttype} -> {data.get('trigger_event', '?')}")
        elif ttype == 'interval':
            secs = data.get('interval_seconds', 0)
            typer.echo(f"  Trigger:  {ttype} -> every {secs}s ({secs // 3600}h {(secs % 3600) // 60}m)")
        elif ttype == 'cron':
            typer.echo(f"  Trigger:  {ttype} -> {data.get('cron_expression', '?')} ({data.get('timezone', 'UTC')})")
        typer.echo(f"  Status:   {data.get('status', '?')} (enabled={data.get('enabled', '?')})")
        typer.echo(f"  On fail:  {data.get('on_failure', 'skip_dependents')}")
        if data.get('last_triggered_at'):
            typer.echo(f"  Last run: {data['last_triggered_at']}")
        if data.get('next_run_at'):
            typer.echo(f"  Next run: {data['next_run_at']}")
        if data.get("description"):
            typer.echo(f"  Desc:     {data['description']}")
        typer.echo()

        steps = data.get("steps", [])
        if steps:
            sorted_steps = sorted(steps, key=lambda s: s.get("order", 0))
            for step in sorted_steps:
                node_type = step.get("node_type", "activity")
                control_type = step.get("control_type") or ""
                if node_type == "control":
                    ref = "-"
                    type_str = {
                        "router": " [ROUTER]", "gate_approval": " [GATE]",
                        "foreach": " [FOREACH]", "gate_wait": " [GATE_WAIT]",
                        "merge": " [MERGE]", "barrier": " [BARRIER]",
                    }.get(control_type, f" [{control_type.upper()}]" if control_type else "")
                else:
                    ref = step.get("activity_slug") or "?"
                    if step.get("activity_version"):
                        ref += f"@v{step['activity_version']}"
                    type_str = ""
                deps = step.get("depends_on_orders", [])
                dep_str = f" [deps: {','.join(str(d) for d in deps)}]" if deps else " [root]"
                loop = ""
                if step.get("loop_to_order") is not None:
                    loop = f" [loop->step {step.get('loop_to_order')}]"
                retries = step.get("max_retries", 0)
                retry_str = f" retries={retries}" if retries else ""
                typer.echo(
                    f"    {step.get('order', '?')}. {step.get('name', '?')} "
                    f"({ref}){type_str}{dep_str}{loop}{retry_str}"
                )
            typer.echo()
        else:
            typer.echo("  No steps yet. Use: kb pipeline add-step")
            typer.echo()
    else:
        emit(data, pretty=False)


@app.command("create")
def create_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug (kebab-case)"),
    name: str = typer.Option(..., "--name", "-n", help="Display name"),
    trigger_type: str = typer.Option("event", "--trigger-type", help="event | manual | interval | cron"),
    trigger_event: Optional[str] = typer.Option(None, "--trigger-event", "-t", help="Event name (for type=event)"),
    interval: Optional[int] = typer.Option(None, "--interval", help="Seconds between runs (for type=interval)"),
    cron: Optional[str] = typer.Option(None, "--cron", help="Cron expression (for type=cron)"),
    on_failure: str = typer.Option("skip_dependents", "--on-failure", help="fail_fast | skip_dependents | all_done"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    default_context: Optional[str] = typer.Option(None, "--default-context", help='JSON default context for manual triggers, e.g. \'{"periodo": "ultimo mes"}\''),
    sequential: bool = typer.Option(False, "--sequential", help="Auto-chain steps by order: each step N automatically depends on step N-1 when added via add-step"),
    execution_class: Optional[str] = typer.Option(
        None, "--execution-class",
        help="workflow (deterministic, required for BI dashboards) | orchestration (allows agents/approvals, default)",
    ),
):
    """Create a new pipeline.

    Examples:
      kb pipeline create fb-deploy --name "Feedback -> Deploy" --trigger-event feedback.created
      kb pipeline create daily-health --name "Daily KB Health" --trigger-type interval --interval 86400
      kb pipeline create report-monthly --name "Monthly Report" --trigger-type manual --default-context '{"periodo": "ultimo mes"}'
      kb pipeline create mi-flujo --name "Mi Flujo" --trigger-type manual --sequential
      kb pipeline create mi-dashboard --name "Mi Dashboard" --execution-class workflow   # for BI
    """
    client = _require_client()

    # Catch common mistake: --trigger-event manual → should be --trigger-type manual
    if trigger_event and trigger_event.lower() == "manual":
        typer.echo("Warning: 'manual' is a trigger TYPE, not an event. Using --trigger-type manual instead.")
        trigger_type = "manual"
        trigger_event = None

    # Auto-infer trigger_type=manual when no trigger source is provided
    if trigger_type == "event" and not trigger_event and interval is None and cron is None:
        trigger_type = "manual"

    payload = {
        "slug": slug,
        "name": name,
        "trigger_type": trigger_type,
        "on_failure": on_failure,
        "status": "active",
        "enabled": True,
    }
    if trigger_event:
        payload["trigger_event"] = trigger_event
    if interval is not None:
        payload["interval_seconds"] = interval
    if cron:
        payload["cron_expression"] = cron
    if description:
        payload["description"] = description
    if default_context:
        try:
            payload["default_context"] = _json.loads(default_context)
        except _json.JSONDecodeError as exc:
            typer.echo(f"Error: --default-context is not valid JSON: {exc}")
            raise typer.Exit(1)
    if sequential:
        payload["metadata"] = {"sequential_mode": True}
    if execution_class:
        payload["execution_class"] = execution_class
    # Pass refresh token for pipeline auth — agent steps use the owner's JWT
    refresh_token = os.environ.get("KB_REFRESH_TOKEN", "")
    if refresh_token:
        payload["refresh_token"] = refresh_token
    data = client.create("pipelines", **payload)
    seq_note = " [sequential]" if sequential else ""
    typer.echo(f"Created pipeline: {slug} (trigger: {trigger_type}, on_failure: {on_failure}){seq_note}")
    if sequential:
        typer.echo("  Modo secuencial: cada paso agregado con order > 1 se encadenará automáticamente al paso anterior.")
    emit(data, pretty=True)


@app.command("run")
def run_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
    context: Optional[str] = typer.Option(None, "--context", "-c", help='JSON context overrides, e.g. \'{"periodo": "marzo 2026"}\''),
):
    """Manually trigger a pipeline run with optional context.

    Context merges with the pipeline's default_context (overrides take precedence).

    Examples:
      kb pipeline run report-monthly
      kb pipeline run report-monthly --context '{"periodo": "marzo 2026"}'
    """
    client = _require_client()
    body = {}
    if context:
        try:
            body["context"] = _json.loads(context)
        except _json.JSONDecodeError as exc:
            typer.echo(f"Error: --context is not valid JSON: {exc}")
            raise typer.Exit(1)
    data = client.post(f"pipelines/{slug}/run", body)
    typer.echo(f"Triggered: {slug}")
    if data.get("context"):
        typer.echo(f"Context: {_json.dumps(data['context'], ensure_ascii=False)}")


@app.command("preflight")
def preflight_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
    params: Optional[str] = typer.Option(None, "--params", "-p", help='JSON params, e.g. \'{"month": "2026-03"}\''),
):
    """Validate that a pipeline can be run with the given params.

    Checks permissions, credentials, structure, and (when the pipeline has a
    declared parameter spec) param types. Prints actionable issues instead
    of erroring out.

    Examples:
      kb pipeline preflight report-monthly
      kb pipeline preflight report-monthly --params '{"month": "2026-03"}'
    """
    client = _require_client()
    body = {}
    if params:
        try:
            body["params"] = _json.loads(params)
        except _json.JSONDecodeError as exc:
            typer.echo(f"Error: --params is not valid JSON: {exc}")
            raise typer.Exit(1)

    data = client.post(f"pipelines/{slug}/preflight", body)
    from ._preflight_render import render_preflight
    render_preflight(data, slug=slug, ready_verb="run")


@app.command("activate")
def activate_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
):
    """Activate a pipeline for yourself (subscribe to triggers)."""
    client = _require_client()
    # Read refresh token from session or env
    refresh_token = os.environ.get("KB_REFRESH_TOKEN", "")
    if not refresh_token:
        from pathlib import Path
        session_file = Path.home() / ".kb" / "session.json"
        if session_file.exists():
            try:
                session = _json.loads(session_file.read_text())
                refresh_token = session.get("refresh_token", "")
            except (_json.JSONDecodeError, TypeError):
                pass
    if not refresh_token:
        typer.echo("Error: no refresh token available. Run `kb auth login` first.")
        raise typer.Exit(1)
    data = client.post(f"pipelines/{slug}/activate", {"refresh_token": refresh_token}, timeout=60.0)
    typer.echo(f"Activated: {slug}")
    if data.get("is_active"):
        typer.echo(f"  Activation ID: {data.get('id')}")


@app.command("deactivate")
def deactivate_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
):
    """Deactivate a pipeline for yourself (unsubscribe from triggers)."""
    client = _require_client()
    client.post(f"pipelines/{slug}/deactivate", {})
    typer.echo(f"Deactivated: {slug}")


@app.command("activations")
def list_activations(
    slug: str = typer.Argument(..., help="Pipeline slug"),
    pretty: bool = typer.Option(False, "--pretty", "-p", help="Pretty-print"),
):
    """List users who have activated this pipeline."""
    client = _require_client()
    data = client.get(f"pipelines/{slug}/activations")
    emit(data, pretty=pretty, columns=["id", "user_email", "is_active", "created_at"], title="Activations")


@app.command("pause")
def pause_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
):
    """Pause a pipeline definition (stops ALL activations from firing)."""
    client = _require_client()
    client.update("pipelines", slug, status="paused")
    typer.echo(f"Paused: {slug}")


@app.command("enable")
def enable_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
):
    """Enable a pipeline (starts accepting triggers)."""
    client = _require_client()
    client.update("pipelines", slug, enabled=True)
    typer.echo(f"Enabled: {slug}")


@app.command("disable")
def disable_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
):
    """Disable a pipeline (stops accepting triggers)."""
    client = _require_client()
    client.update("pipelines", slug, enabled=False)
    typer.echo(f"Disabled: {slug}")


@app.command("delete")
def delete_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
):
    """Delete a pipeline and all its steps."""
    client = _require_client()
    client.delete("pipelines", slug)
    typer.echo(f"Deleted: {slug}")


@app.command("update")
def update_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Display name"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    trigger_type: Optional[str] = typer.Option(None, "--trigger-type", help="event | manual | interval | cron"),
    trigger_event: Optional[str] = typer.Option(None, "--trigger-event", "-t", help="Event name"),
    interval: Optional[int] = typer.Option(None, "--interval", help="Seconds between runs"),
    cron: Optional[str] = typer.Option(None, "--cron", help="Cron expression"),
    on_failure: Optional[str] = typer.Option(None, "--on-failure", help="fail_fast | skip_dependents | all_done"),
    max_concurrent: Optional[int] = typer.Option(None, "--max-concurrent", help="Max concurrent runs"),
    default_context: Optional[str] = typer.Option(None, "--default-context", help="JSON default context"),
    execution_class: Optional[str] = typer.Option(
        None, "--execution-class",
        help="workflow | orchestration",
    ),
):
    """Update pipeline fields.

    Examples:
      kb pipeline update fb-deploy --name "New Name" --on-failure fail_fast
      kb pipeline update daily-health --max-concurrent 2
      kb pipeline update report --default-context '{"periodo": "abril 2026"}'
      kb pipeline update mi-dashboard --execution-class workflow
    """
    client = _require_client()
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if trigger_type is not None:
        payload["trigger_type"] = trigger_type
    if trigger_event is not None:
        payload["trigger_event"] = trigger_event
    if interval is not None:
        payload["interval_seconds"] = interval
    if cron is not None:
        payload["cron_expression"] = cron
    if on_failure is not None:
        payload["on_failure"] = on_failure
    if max_concurrent is not None:
        payload["max_concurrent_runs"] = max_concurrent
    if default_context is not None:
        try:
            payload["default_context"] = _json.loads(default_context)
        except _json.JSONDecodeError as exc:
            typer.echo(f"Error: --default-context is not valid JSON: {exc}")
            raise typer.Exit(1)
    if execution_class is not None:
        payload["execution_class"] = execution_class

    if not payload:
        typer.echo("Error: provide at least one field to update")
        raise typer.Exit(1)

    data = client.update("pipelines", slug, **payload)
    typer.echo(f"Updated pipeline: {slug}")
    emit(data, pretty=True)


@app.command("update-step")
def update_step(
    pipeline_slug: str = typer.Argument(..., help="Pipeline slug"),
    order: int = typer.Option(..., "--order", "-o", help="Step order to update"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Step name"),
    new_order: Optional[int] = typer.Option(None, "--new-order", help="New order position"),
    node_type: Optional[str] = typer.Option(None, "--node-type", help="activity | control"),
    activity_slug: Optional[str] = typer.Option(None, "--activity", "-a", help="Activity slug (for node_type=activity)"),
    activity_version: Optional[int] = typer.Option(None, "--activity-version", help="Pinned Activity version (default: latest)"),
    inputs: Optional[str] = typer.Option(None, "--inputs", help="Step inputs JSON (templates: {{steps.NAME.items}} where NAME is the dep step's --name, not its order; {{trigger.KEY}})"),
    claims: Optional[str] = typer.Option(None, "--claims", help="Claims JSON: '[{\"entity\":\"person\",\"id\":\"{{trigger.id}}\",\"mode\":\"write\"}]'"),
    conflict_policy: Optional[str] = typer.Option(None, "--conflict-policy", help="wait | skip | fail (on claim conflict)"),
    control_type: Optional[str] = typer.Option(None, "--control-type", help="router | foreach | gate_approval | gate_wait | merge | barrier"),
    control_config: Optional[str] = typer.Option(None, "--control-config", help="Control node config JSON"),
    timeout_override: Optional[int] = typer.Option(None, "--timeout-override", help="Per-step timeout override (seconds)"),
    retries: Optional[int] = typer.Option(None, "--retries", help="Max retries"),
    retry_delay: Optional[int] = typer.Option(None, "--retry-delay", help="Base delay between retries (seconds)"),
    max_retry_delay: Optional[int] = typer.Option(None, "--max-retry-delay", help="Max delay cap (seconds)"),
    loop_to: Optional[int] = typer.Option(None, "--loop-to", help="Step order to loop back to"),
    max_loops: Optional[int] = typer.Option(None, "--max-loops", help="Max loop iterations"),
    depends_on: Optional[str] = typer.Option(None, "--depends-on", help="Comma-separated step orders this depends on (e.g. '1,2'). Replaces current dependencies."),
):
    """Update a step in a pipeline by order number.

    Examples:
      kb pipeline update-step fb-pipe --order 3 --activity triage-bot --inputs '{"item": "{{trigger.payload}}"}'
      kb pipeline update-step fb-pipe --order 4 --loop-to 2 --max-loops 5
      kb pipeline update-step fb-pipe --order 3 --node-type control --control-type gate_approval \\
          --control-config '{"title_template": "Gate: {title}"}'
      kb pipeline update-step fb-pipe --order 4 --depends-on 2,3
    """
    client = _require_client()

    # Fetch all steps — needed for depends_on and loop_to resolution
    steps = client.list("pipeline-steps", pipeline=pipeline_slug)
    target = None
    for s in steps:
        if s.get("order") == order:
            target = s
            break
    if not target:
        typer.echo(f"No step with order {order} in {pipeline_slug}")
        raise typer.Exit(1)

    payload = {}
    if name is not None:
        payload["name"] = name
    if new_order is not None:
        payload["order"] = new_order
    if retries is not None:
        payload["max_retries"] = retries
    if retry_delay is not None:
        payload["retry_delay_seconds"] = retry_delay
    if max_retry_delay is not None:
        payload["max_retry_delay_seconds"] = max_retry_delay
    if max_loops is not None:
        payload["max_loops"] = max_loops
    if timeout_override is not None:
        payload["timeout_seconds_override"] = timeout_override

    # Activity / node_type fields — pass through as-is; the API validates.
    if node_type is not None:
        if node_type not in ("activity", "control"):
            typer.echo(f"Error: --node-type must be 'activity' or 'control', got '{node_type}'")
            raise typer.Exit(1)
        payload["node_type"] = node_type
    if activity_slug is not None:
        payload["activity_slug"] = activity_slug
    if activity_version is not None:
        payload["activity_version"] = activity_version
    if control_type is not None:
        payload["control_type"] = control_type
    if conflict_policy is not None:
        payload["conflict_policy"] = conflict_policy

    # JSON payloads
    for field_name, raw in (("inputs", inputs), ("claims", claims), ("control_config", control_config)):
        if raw is not None:
            try:
                payload[field_name] = _json.loads(raw)
            except _json.JSONDecodeError as exc:
                typer.echo(f"Error: --{field_name.replace('_', '-')} is not valid JSON: {exc}")
                raise typer.Exit(1)

    # Resolve loop_to order → step ID
    if loop_to is not None:
        order_to_id = {s["order"]: s["id"] for s in steps}
        if loop_to not in order_to_id:
            typer.echo(f"Error: no step with order {loop_to} in {pipeline_slug}")
            raise typer.Exit(1)
        payload["loop_to"] = order_to_id[loop_to]

    # Resolve depends_on: convert step orders to step IDs (replaces current deps)
    if depends_on is not None:
        order_to_id = {s["order"]: s["id"] for s in steps}
        dep_orders = [int(o.strip()) for o in depends_on.split(",") if o.strip()]
        dep_ids = []
        for dep_order in dep_orders:
            if dep_order == order:
                typer.echo(f"Error: step {order} cannot depend on itself")
                raise typer.Exit(1)
            if dep_order not in order_to_id:
                typer.echo(f"Error: no step with order {dep_order} in {pipeline_slug}")
                raise typer.Exit(1)
            dep_ids.append(order_to_id[dep_order])
        payload["depends_on"] = dep_ids

    if not payload:
        typer.echo("Error: provide at least one field to update")
        raise typer.Exit(1)

    data = client.update("pipeline-steps", target["id"], **payload)
    typer.echo(f"Updated step {order} in {pipeline_slug}")
    emit(data, pretty=True)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


@app.command("add-step")
def add_step(
    pipeline_slug: str = typer.Argument(..., help="Pipeline slug"),
    name: str = typer.Option(..., "--name", "-n", help="Step name"),
    order: int = typer.Option(..., "--order", "-o", help="Step order (1, 2, 3...)"),
    node_type: str = typer.Option("activity", "--node-type", help="activity | control"),
    activity_slug: Optional[str] = typer.Option(None, "--activity", "-a", help="Activity slug (required for node_type=activity)"),
    activity_version: Optional[int] = typer.Option(None, "--activity-version", help="Pinned Activity version (default: latest at snapshot)"),
    inputs: Optional[str] = typer.Option(None, "--inputs", help="Step inputs JSON (templates: {{steps.NAME.items}} where NAME is the dep step's --name, not its order; {{trigger.KEY}})"),
    claims: Optional[str] = typer.Option(None, "--claims", help="Claims JSON: '[{\"entity\":\"person\",\"id\":\"{{trigger.id}}\",\"mode\":\"write\"}]'"),
    conflict_policy: str = typer.Option("wait", "--conflict-policy", help="wait | skip | fail"),
    claim_timeout: int = typer.Option(60, "--claim-timeout", help="Seconds to wait on claim conflict before retry/skip/fail"),
    timeout_override: Optional[int] = typer.Option(None, "--timeout-override", help="Per-step timeout override (seconds)"),
    control_type: Optional[str] = typer.Option(None, "--control-type", help="router | foreach | gate_approval | gate_wait | merge | barrier"),
    control_config: Optional[str] = typer.Option(None, "--control-config", help="Control node config JSON (router: branches; foreach: target_pipeline_slug; gate_approval: title_template)"),
    depends_on: Optional[str] = typer.Option(None, "--depends-on", help="Comma-separated step orders this depends on (e.g. '1,2')"),
    sequential: bool = typer.Option(False, "--sequential", help="Auto-depend on the immediately preceding step (order N-1)"),
    retries: int = typer.Option(0, "--retries", help="Max retries on failure"),
    retry_delay: int = typer.Option(60, "--retry-delay", help="Base delay between retries (seconds)"),
    retry_backoff: bool = typer.Option(True, "--retry-backoff/--no-retry-backoff", help="Exponential backoff"),
    max_retry_delay: int = typer.Option(600, "--max-retry-delay", help="Max delay cap (seconds)"),
    loop_to: Optional[int] = typer.Option(None, "--loop-to", help="Step order to loop back to on <<LOOP_BACK>>"),
    max_loops: int = typer.Option(3, "--max-loops", help="Max loop iterations"),
):
    """Add a step to a pipeline.

    Steps without --depends-on run in parallel (as root nodes in the DAG).
    Use --depends-on to declare sequential dependencies, or --sequential as
    a shorthand for 'depend on the immediately preceding step'.

    Examples:
      # Activity invocations (most common):
      kb pipeline add-step fb-pipe --activity feedback-triager --name "Triage" --order 1
      kb pipeline add-step fb-pipe --activity issue-analyzer --name "Analyze" --order 2 --depends-on 1 \\
          --inputs '{"item": "{{steps.triage.items[0]}}"}'
      kb pipeline add-step fb-pipe --activity code-implementer --name "Implement" --order 3 --sequential \\
          --claims '[{"entity":"issue","id":"{{trigger.issue_id}}","mode":"write"}]'
      # Control nodes:
      kb pipeline add-step fb-pipe --node-type control --control-type router --name "Route" --order 2 \\
          --depends-on 1 --control-config '{"branches": {"bug": [3], "feature": [4]}}'
      kb pipeline add-step fb-pipe --node-type control --control-type gate_approval --name "Approve" --order 5 \\
          --depends-on 4 --control-config '{"title_template": "Approve: {title}"}'
    """
    import json as _json

    client = _require_client()

    if node_type not in ("activity", "control"):
        typer.echo(f"Error: --node-type must be 'activity' or 'control', got '{node_type}'")
        raise typer.Exit(1)

    if node_type == "activity" and not activity_slug:
        typer.echo("Error: --activity is required for node_type=activity")
        raise typer.Exit(1)

    if node_type == "control" and not control_type:
        typer.echo("Error: --control-type is required for node_type=control")
        raise typer.Exit(1)

    if sequential and depends_on:
        typer.echo("Error: --sequential y --depends-on son mutuamente excluyentes. Usa uno o el otro.")
        raise typer.Exit(1)

    # --sequential: shorthand for --depends-on (order - 1)
    if sequential:
        if order <= 1:
            typer.echo("Warning: --sequential no tiene efecto en el paso 1 (no hay paso previo). El paso se creará sin dependencias.")
            sequential = False
        else:
            depends_on = str(order - 1)

    # Resolve pipeline
    pipeline = client.get(f"pipelines/{pipeline_slug}")
    pipeline_id = pipeline["id"]

    # Check pipeline-level sequential_mode (set via `kb pipeline create --sequential`)
    pipeline_sequential_mode = (pipeline.get("metadata") or {}).get("sequential_mode", False)
    if pipeline_sequential_mode and not depends_on and order > 1:
        depends_on = str(order - 1)
        typer.echo(f"  [sequential mode] Encadenando automáticamente: depende del paso {order - 1}.")

    payload = {
        "pipeline": pipeline_id,
        "name": name,
        "order": order,
        "node_type": node_type,
        "conflict_policy": conflict_policy,
        "claim_timeout_seconds": claim_timeout,
        "max_retries": retries,
        "retry_delay_seconds": retry_delay,
        "retry_backoff": retry_backoff,
        "max_retry_delay_seconds": max_retry_delay,
        "max_loops": max_loops,
    }
    if timeout_override is not None:
        payload["timeout_seconds_override"] = timeout_override

    # Activity-invocation fields
    if node_type == "activity":
        payload["activity_slug"] = activity_slug
        if activity_version is not None:
            payload["activity_version"] = activity_version

    # Control-node fields
    if node_type == "control":
        payload["control_type"] = control_type

    # JSON payloads (inputs / claims / control_config)
    for field_name, raw in (("inputs", inputs), ("claims", claims), ("control_config", control_config)):
        if raw:
            try:
                payload[field_name] = _json.loads(raw)
            except _json.JSONDecodeError as exc:
                typer.echo(f"Error: --{field_name.replace('_', '-')} is not valid JSON: {exc}")
                raise typer.Exit(1)

    # Fetch existing steps once if either depends_on or loop_to needs them
    existing_steps: list | None = None
    if depends_on or loop_to is not None:
        existing_steps = client.list("pipeline-steps", pipeline=pipeline_slug)

    # Resolve depends_on: convert step orders to step IDs
    dep_ids = []
    if depends_on:
        assert existing_steps is not None
        dep_orders = [int(o.strip()) for o in depends_on.split(",")]
        order_to_id = {s["order"]: s["id"] for s in existing_steps}
        for dep_order in dep_orders:
            if dep_order not in order_to_id:
                typer.echo(f"Error: no step with order {dep_order} in {pipeline_slug}")
                raise typer.Exit(1)
            dep_ids.append(order_to_id[dep_order])
        payload["depends_on"] = dep_ids
    elif order > 1:
        typer.echo(
            f"Warning: el paso {order} no tiene dependencias declaradas y se ejecutará en paralelo "
            f"con los demás pasos raíz.\n"
            f"  ¿Querías --depends-on {order - 1}? Si es intencional, ignora este mensaje.\n"
            f"  Tip: usa --sequential para encadenar automáticamente al paso anterior."
        )

    # Resolve loop_to: convert step order to step ID
    if loop_to is not None:
        assert existing_steps is not None
        order_to_id = {s["order"]: s["id"] for s in existing_steps}
        if loop_to not in order_to_id:
            typer.echo(f"Error: no step with order {loop_to} in {pipeline_slug}")
            raise typer.Exit(1)
        payload["loop_to"] = order_to_id[loop_to]

    # Idempotency: if a step with this order already exists, update it.
    existing_at_order = None
    if existing_steps is not None:
        existing_at_order = next((s for s in existing_steps if s.get("order") == order), None)
    else:
        all_steps = client.list("pipeline-steps", pipeline=pipeline_slug)
        existing_at_order = next((s for s in all_steps if s.get("order") == order), None)

    def _describe_label() -> str:
        if node_type == "control":
            return f"control:{control_type}"
        ref = activity_slug or "?"
        if activity_version:
            ref += f"@v{activity_version}"
        return ref

    def _tags() -> str:
        tags = []
        if node_type == "control" and control_type:
            tags.append(control_type.upper())
        if dep_ids:
            tags.append(f"deps:{depends_on}")
        if loop_to is not None:
            tags.append(f"loop->step {loop_to}")
        return f" [{', '.join(tags)}]" if tags else ""

    if existing_at_order:
        typer.echo(
            f"  [idempotent] Step {order} already exists in {pipeline_slug} "
            f"(name: '{existing_at_order.get('name', '?')}'). Updating instead of creating."
        )
        update_payload = {k: v for k, v in payload.items() if k != "pipeline"}
        data = client.update("pipeline-steps", existing_at_order["id"], **update_payload)
        typer.echo(f"Updated step {order}: {name} ({_describe_label()}){_tags()}")
        emit(data, pretty=True)
        return

    data = client.create("pipeline-steps", **payload)
    typer.echo(f"Added step {order}: {name} ({_describe_label()}){_tags()}")
    emit(data, pretty=True)


@app.command("remove-step")
def remove_step(
    pipeline_slug: str = typer.Argument(..., help="Pipeline slug"),
    order: int = typer.Option(..., "--order", "-o", help="Step order to remove"),
):
    """Remove a step from a pipeline by order number.

    Dependents of the removed step are automatically reconnected to the removed
    step's own dependencies (DAG re-wiring). If the removed step was a root node,
    its dependents become new root nodes.

    Examples:
      kb pipeline remove-step fb-pipe --order 3
    """
    client = _require_client()
    steps = client.list("pipeline-steps", pipeline=pipeline_slug)
    target = None
    for s in steps:
        if s.get("order") == order:
            target = s
            break
    if not target:
        typer.echo(f"No step with order {order} in {pipeline_slug}")
        raise typer.Exit(1)

    # Identify dependents (steps that list this step in depends_on_orders)
    dependents = [s for s in steps if order in (s.get("depends_on_orders") or [])]
    parent_orders = target.get("depends_on_orders") or []

    client.delete("pipeline-steps", target["id"])
    typer.echo(f"Removed step {order} from {pipeline_slug}")

    # Report how the DAG was re-wired (backend handles the actual reconnection)
    if dependents:
        dep_names = ", ".join(f"step {s['order']} ({s.get('name', '?')})" for s in dependents)
        if parent_orders:
            typer.echo(
                f"  DAG re-wired: {dep_names} now depend on {parent_orders} "
                f"(inherited from removed step {order})."
            )
        else:
            typer.echo(
                f"  DAG re-wired: {dep_names} promoted to root node(s) "
                f"(removed step {order} had no parents)."
            )


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


@app.command("runs")
def list_runs(
    pipeline: Optional[str] = typer.Option(None, "--pipeline", "-p"),
    status: Optional[str] = typer.Option(None, "--status", "-s"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List pipeline runs."""
    client = _require_client()
    params = {}
    if pipeline:
        params["pipeline"] = pipeline
    if status:
        params["status"] = status
    data = client.list("pipeline-runs", **params)
    emit(
        data, pretty=pretty,
        columns=["id", "pipeline_slug", "status", "current_step_order",
                 "total_steps", "started_at", "finished_at"],
        title="Pipeline Runs",
    )


@app.command("run-show")
def show_run(
    run_id: int = typer.Argument(..., help="Pipeline run ID"),
    pretty: bool = typer.Option(True, "--pretty/--no-pretty"),
    full: bool = typer.Option(
        False, "--full",
        help="Show complete output/error without truncation. Failed steps "
             "always get their full error printed regardless of this flag.",
    ),
):
    """Show detailed status of a pipeline run with per-step output."""
    client = _require_client()
    data = client.get(f"pipeline-runs/{run_id}")

    if pretty:
        typer.echo(f"\n  Run #{data['id']} — {data.get('pipeline_name', '?')}")
        typer.echo(f"  Status:  {data['status']}")
        typer.echo(f"  Trigger: {data.get('trigger_event', '?')}")
        if data.get('started_at'):
            typer.echo(f"  Started: {data['started_at']}")
        if data.get('finished_at'):
            typer.echo(f"  Finished: {data['finished_at']}")
        typer.echo()

        # Output summary
        output = data.get("output")
        if output and output.get("summary"):
            typer.echo(f"  Summary: {output['summary']}")
            typer.echo()

        # Metrics (Fase 5)
        metrics = data.get("metrics")
        if metrics:
            typer.echo("  Metrics:")
            typer.echo(f"    duration:     {metrics.get('duration_seconds', 0)}s")
            typer.echo(f"    queue wait:   {metrics.get('queue_wait_seconds', 0)}s")
            typer.echo(
                f"    steps:        {metrics.get('steps_completed', 0)} ok, "
                f"{metrics.get('steps_failed', 0)} failed, "
                f"{metrics.get('steps_skipped', 0)} skipped",
            )
            if metrics.get("retries"):
                typer.echo(f"    retries:      {metrics['retries']}")
            if metrics.get("error_codes"):
                codes = ", ".join(f"{k}={v}" for k, v in metrics["error_codes"].items())
                typer.echo(f"    error codes:  {codes}")
            typer.echo()

        # Steps
        steps = data.get("steps", [])
        if steps:
            typer.echo("  Steps:")
            for step in steps:
                status_icon = {
                    "completed": "+",
                    "failed": "X",
                    "skipped": "-",
                    "running": ">",
                    "waiting_retry": "~",
                    "waiting_approval": "?",
                    "pending": ".",
                    "queued": ".",
                }.get(step.get("status", ""), " ")

                deps = step.get("depends_on", [])
                dep_str = f" deps:[{','.join(str(d) for d in deps)}]" if deps else ""
                attempt_str = f" attempt:{step.get('attempt', 0)}" if step.get("attempt", 0) > 1 else ""
                loop_str = f" loops:{step.get('loop_count', 0)}" if step.get("loop_count", 0) > 0 else ""

                # Show activity or control type instead of the legacy agent slug.
                if step.get("node_type") == "control":
                    ref = f"control:{step.get('control_type', '?')}"
                elif step.get("activity_slug"):
                    ref = f"activity:{step['activity_slug']}"
                    if step.get("activity_version"):
                        ref += f"@v{step['activity_version']}"
                else:
                    ref = "(unconfigured)"

                typer.echo(
                    f"    [{status_icon}] {step.get('order', '?')}. {step.get('name', '?')} "
                    f"({ref}) — {step.get('status', '?')}"
                    f"{dep_str}{attempt_str}{loop_str}"
                )
                if step.get("output"):
                    if full:
                        typer.echo(f"        Output:\n{step['output']}")
                    else:
                        preview = step["output"][:200].replace("\n", " ")
                        typer.echo(f"        Output: {preview}")
                if step.get("error"):
                    code = step.get("error_code") or ""
                    code_str = f"[{code}] " if code else ""
                    # Failed steps always get the full traceback — truncating defeats debugging.
                    step_failed = step.get("status") == "failed"
                    if full or step_failed:
                        typer.echo(f"        Error:  {code_str}")
                        for line in step["error"].splitlines():
                            typer.echo(f"          {line}")
                    else:
                        preview = step["error"][:200].replace("\n", " ")
                        typer.echo(f"        Error:  {code_str}{preview}")
            typer.echo()

        # Errors summary
        if output and output.get("errors"):
            typer.echo("  Errors:")
            for err in output["errors"]:
                err_body = err["error"] if full else err["error"][:200]
                typer.echo(
                    f"    Step {err['step']} ({err['name']}): "
                    f"(attempts: {err.get('attempts', '?')})"
                )
                for line in err_body.splitlines() or [err_body]:
                    typer.echo(f"      {line}")
            typer.echo()

        # Actions hint
        if data["status"] == "failed":
            rid = data["id"]
            typer.echo("  Actions:")
            typer.echo(f"    kb pipeline retry {rid}              # resume all failed steps")
            typer.echo(f"    kb pipeline retry {rid} --step N     # retry specific step")
            typer.echo(f"    kb pipeline skip {rid} --step N      # skip step and continue")
            typer.echo()
    else:
        emit(data, pretty=False)


@app.command("retry")
def retry_run(
    run_id: int = typer.Argument(..., help="Pipeline run ID"),
    step: Optional[int] = typer.Option(None, "--step", "-s", help="Specific step order to retry"),
):
    """Retry a failed pipeline run or a specific failed step.

    Without --step: resumes the entire pipeline (retries all failed, unblocks skipped).
    With --step N: retries only step N.

    Examples:
      kb pipeline retry 42              # resume all
      kb pipeline retry 42 --step 3     # retry step 3 only
    """
    client = _require_client()
    if step is not None:
        client.post(f"pipeline-runs/{run_id}/retry/{step}")
        typer.echo(f"Retrying step {step} of run {run_id}")
    else:
        client.post(f"pipeline-runs/{run_id}/resume")
        typer.echo(f"Resuming run {run_id} — retrying all failed steps")


@app.command("skip")
def skip_step_cmd(
    run_id: int = typer.Argument(..., help="Pipeline run ID"),
    step: int = typer.Option(..., "--step", "-s", help="Step order to skip"),
):
    """Skip a failed step and continue the pipeline.

    Example:
      kb pipeline skip 42 --step 3
    """
    client = _require_client()
    client.post(f"pipeline-runs/{run_id}/skip/{step}")
    typer.echo(f"Skipped step {step} of run {run_id} — pipeline continuing")


def _ordinal_ref_hint(ref: str, dep_names: set) -> str:
    """Suffix explaining the NAME-vs-order mistake when a bad ref is numeric."""
    if not ref.isdigit():
        return ""
    available = sorted(n for n in dep_names if n)
    return (
        f" — '{ref}' looks like an ordinal; step refs use NAMES, "
        f"not order numbers. Available dep names: {available}"
    )


@app.command("lint")
def lint_pipeline(
    slug: str = typer.Argument(..., help="Pipeline slug"),
):
    """Statically validate a pipeline: DAG, template refs, control configs.

    Runs a set of checks that would otherwise only surface at execution
    time (template typos, missing dependencies, malformed control config).
    Reports ERRORs and WARNINGs; exits non-zero if any ERROR is found.
    """
    import re

    client = _require_client()
    data = client.get(f"pipelines/{slug}")

    errors: list[str] = []
    warnings: list[str] = []

    steps = data.get("steps", []) or []
    names_by_order = {s["order"]: s["name"] for s in steps}
    step_by_name = {s["name"]: s for s in steps}

    placeholder_re = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")

    def _walk_strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for v in value.values():
                yield from _walk_strings(v)
        elif isinstance(value, list):
            for v in value:
                yield from _walk_strings(v)

    def _referenced_steps(payload) -> set:
        refs = set()
        for s in _walk_strings(payload):
            for m in placeholder_re.finditer(s):
                expr = m.group(1).strip()
                if expr.startswith("steps."):
                    parts = expr.split(".", 2)
                    if len(parts) >= 2:
                        name = parts[1].split("[", 1)[0]
                        if name:
                            refs.add(name)
        return refs

    for step in steps:
        order = step.get("order")
        name = step.get("name", "?")
        node_type = step.get("node_type", "activity")
        # `depends_on` is a list of PipelineStep IDs in the pipeline
        # serializer; `depends_on_orders` is the ordinal view. We use
        # the ordinal view because template refs resolve by step name
        # (and name→order via names_by_order).
        deps_orders = step.get("depends_on_orders", []) or []
        dep_names = {names_by_order.get(o) for o in deps_orders}
        dep_names.discard(None)

        if node_type == "activity":
            if not step.get("activity_slug"):
                errors.append(f"[ERROR] step {order} ({name}): activity_slug is empty")
            # Template references in inputs must be in depends_on
            inputs = step.get("inputs") or {}
            for ref in _referenced_steps(inputs):
                if ref not in dep_names:
                    errors.append(
                        f"[ERROR] step {order} ({name}): references {{{{steps.{ref}…}}}} "
                        f"but {ref!r} is not in depends_on{_ordinal_ref_hint(ref, dep_names)}"
                    )
            # Same for claims id templates
            claims = step.get("claims") or []
            for i, claim in enumerate(claims):
                for ref in _referenced_steps(claim.get("id")):
                    if ref not in dep_names:
                        errors.append(
                            f"[ERROR] step {order} ({name}): claim[{i}] references "
                            f"{{{{steps.{ref}…}}}} but {ref!r} is not in depends_on{_ordinal_ref_hint(ref, dep_names)}"
                        )
        elif node_type == "control":
            ctype = step.get("control_type")
            if not ctype:
                errors.append(f"[ERROR] step {order} ({name}): control_type is empty")
            config = step.get("control_config") or {}
            if ctype == "router":
                branches = config.get("branches", {})
                if not branches:
                    errors.append(f"[ERROR] step {order} ({name}): router with no branches")
                for branch_key, orders in branches.items():
                    if branch_key == "__terminate__":
                        continue
                    orders_list = orders if isinstance(orders, list) else [orders]
                    for o in orders_list:
                        if o not in names_by_order:
                            errors.append(
                                f"[ERROR] step {order} ({name}): router branch {branch_key!r} "
                                f"references step order {o} not in pipeline"
                            )
            elif ctype == "foreach":
                if not config.get("target_pipeline_slug"):
                    errors.append(
                        f"[ERROR] step {order} ({name}): foreach missing target_pipeline_slug"
                    )
        else:
            errors.append(f"[ERROR] step {order} ({name}): unknown node_type {node_type!r}")

    # execution_class coherence (warning only — composition decision)
    exec_class = data.get("execution_class")
    if exec_class == "workflow":
        for step in steps:
            if step.get("node_type") == "control" and step.get("control_type") == "gate_approval":
                warnings.append(
                    f"[WARN] step {step.get('order')} ({step.get('name')}): "
                    f"gate_approval in execution_class=workflow will block at runtime "
                    f"(BI refuses to render such pipelines)"
                )

    if not errors and not warnings:
        typer.echo(f"[OK] {slug}: no issues found in {len(steps)} steps")
        return

    for line in errors:
        typer.echo(line)
    for line in warnings:
        typer.echo(line)

    typer.echo(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        raise typer.Exit(code=1)
