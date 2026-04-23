"""kb report — Manage Reports (pipeline-backed file artifacts).

Replaces the old ``kb view`` command. A Report pairs a Pipeline with a
declared parameter spec; variants (generated files) ship in F3.
"""

from __future__ import annotations

import json as _json
from typing import List, Optional

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


def _parse_json(raw: Optional[str], field_name: str):
    if raw is None:
        return None
    try:
        return _json.loads(raw)
    except _json.JSONDecodeError as exc:
        import sys
        print(f"Error: {field_name} is not valid JSON: {exc}", file=sys.stderr)
        raise typer.Exit(1)


app = typer.Typer(help="Report management — pipeline-backed file artifacts")


# ---------------------------------------------------------------------------
# Parameter shorthand parsing
# ---------------------------------------------------------------------------


def _parse_param_shorthand(spec: str) -> dict:
    """Parse 'NAME:TYPE[:LABEL]' into a parameter spec dict.

    Examples:
      'month:month:Mes'  -> {"name":"month","type":"month","label":"Mes"}
      'enabled:boolean'  -> {"name":"enabled","type":"boolean"}
    """
    parts = spec.split(":", 2)
    if len(parts) < 2:
        import sys
        print(
            f"Error: --param must be 'NAME:TYPE' or 'NAME:TYPE:LABEL', got {spec!r}",
            file=sys.stderr,
        )
        raise typer.Exit(1)
    out: dict = {"name": parts[0], "type": parts[1]}
    if len(parts) >= 3:
        out["label"] = parts[2]
    return out


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@app.command("create")
def create_report(
    slug: str = typer.Argument(..., help="Report slug (kebab-case)"),
    name: str = typer.Option(..., "--name", "-n", help="Display name"),
    pipeline: str = typer.Option(..., "--pipeline", "-p", help="Slug of the Pipeline that generates this report"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    parameters: Optional[str] = typer.Option(
        None, "--parameters",
        help='JSON list of param specs: [{"name":"month","type":"month","required":true,"label":"Mes"}, ...]. '
             'type ∈ {boolean, number, integer, date, month, year, string, enum, reference}. '
             'For simple cases prefer repeated --param NAME:TYPE[:LABEL].',
    ),
    param: Optional[List[str]] = typer.Option(
        None, "--param",
        help="Shorthand for a single parameter: NAME:TYPE[:LABEL]. Repeatable.",
    ),
    output_format: str = typer.Option(
        "xlsx", "--output-format", "-o",
        help="xlsx | docx | pdf | csv | html | json (hint for UI)",
    ),
    tags: Optional[List[str]] = typer.Option(None, "--tag", help="Free-form tag. Repeatable."),
    visibility: str = typer.Option("org", "--visibility", "-V", help="org | restricted | private"),
    org_level: str = typer.Option("read", "--org-level", help="read | comment | write"),
):
    """Create a new Report.

    Examples:
      # JSON full-form:
      kb report create cobranza-mensual --name "Cobranza mensual" --pipeline report-cobranza-mensual \\
        --parameters '[{"name":"month","type":"month","required":true,"label":"Mes"}]'

      # Shorthand:
      kb report create facturas-por-mes --name "Facturas por mes" --pipeline fact-mensual \\
        --param month:month:Mes --param incluir_anuladas:boolean
    """
    client = _require_client()

    resolved_params = None
    if parameters is not None:
        resolved_params = _parse_json(parameters, "parameters")
    elif param:
        resolved_params = [_parse_param_shorthand(p) for p in param]

    payload: dict = {
        "slug": slug,
        "name": name,
        "pipeline": pipeline,
        "output_format": output_format,
        "visibility": visibility,
        "org_level": org_level,
    }
    if description is not None:
        payload["description"] = description
    if module is not None:
        payload["module"] = module
    if resolved_params is not None:
        payload["parameters"] = resolved_params
    if tags:
        payload["tags"] = list(tags)

    data = client.post("reports/", payload)
    emit(data)


@app.command("list")
def list_reports(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pipeline: Optional[str] = typer.Option(None, "--pipeline", "-p"),
    tag: Optional[str] = typer.Option(None, "--tag"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List Reports visible to the current user."""
    client = _require_client()
    kwargs = {}
    if module:
        kwargs["module"] = module
    if pipeline:
        kwargs["pipeline"] = pipeline
    if tag:
        kwargs["tag"] = tag
    data = client.list("reports", **kwargs)
    emit(
        data,
        pretty=pretty,
        columns=["id", "slug", "name", "pipeline", "output_format", "module", "visibility"],
        title="Reports",
    )


@app.command("show")
def show_report(
    slug: str = typer.Argument(..., help="Report slug"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a Report's config."""
    client = _require_client()
    data = client.show("reports", slug)
    emit(data, pretty=pretty, title=f"Report: {data.get('name', slug)}")


@app.command("update")
def update_report(
    slug: str = typer.Argument(..., help="Report slug"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    pipeline: Optional[str] = typer.Option(None, "--pipeline", "-p"),
    parameters: Optional[str] = typer.Option(None, "--parameters"),
    output_format: Optional[str] = typer.Option(None, "--output-format", "-o"),
    visibility: Optional[str] = typer.Option(None, "--visibility", "-V"),
    org_level: Optional[str] = typer.Option(None, "--org-level"),
):
    """Update a Report's config. Only provided fields are changed."""
    client = _require_client()
    payload: dict = {}
    for key, raw_val in [
        ("name", name), ("description", description), ("module", module),
        ("pipeline", pipeline), ("output_format", output_format),
        ("visibility", visibility), ("org_level", org_level),
    ]:
        if raw_val is not None:
            payload[key] = raw_val
    if parameters is not None:
        payload["parameters"] = _parse_json(parameters, "parameters")

    data = client.update("reports", slug, **payload)
    emit(data)


@app.command("delete")
def delete_report(
    slug: str = typer.Argument(..., help="Report slug"),
):
    """Delete a Report."""
    client = _require_client()
    client.delete("reports", slug)
    emit({"slug": slug, "deleted": True})


@app.command("generate")
def generate_report(
    slug: str = typer.Argument(..., help="Report slug"),
    params: Optional[str] = typer.Option(None, "--params", help='JSON params, e.g. \'{"month":"2026-03"}\''),
    force: bool = typer.Option(
        False, "--force",
        help="If an active variant with the same params exists, delete it (including "
             "its generated Documents) and regenerate in one step.",
    ),
    timeout: int = typer.Option(
        300, "--timeout",
        help="Max seconds to wait for the pipeline to finish after the kickoff "
             "response. Only affects the CLI polling loop; the backend continues "
             "independently even if the CLI stops waiting.",
    ),
    no_wait: bool = typer.Option(
        False, "--no-wait",
        help="Return immediately after the 202 kickoff response without polling "
             "for completion. Useful for scripted pipelines that will check "
             "status later.",
    ),
):
    """Generate a new variant of a Report by running its pipeline.

    The backend responds 202 Accepted immediately after creating the variant
    and queueing the pipeline. This command then polls the variant until it
    reaches a terminal status (``completed`` / ``failed``) or ``--timeout``
    seconds pass, printing the final result and the download URL when the
    variant completes.

    Exit codes:
      0 — variant completed successfully
      1 — preflight failed (400)
      2 — duplicate variant (409) without --force, or polling timed out
      3 — variant reached status=failed
    """
    import time as _time
    from ..client.http import APIError

    client = _require_client()
    body = {}
    if params:
        body["params"] = _parse_json(params, "params")

    def _do_generate():
        return client.post(f"reports/{slug}/generate", body)

    try:
        data = _do_generate()
    except APIError as e:
        if e.status_code == 409 and force:
            import json as _json
            import re
            existing_id = None
            try:
                parsed = _json.loads(e.detail) if isinstance(e.detail, str) else e.detail
                existing_id = (parsed or {}).get("existing_variant", {}).get("id")
            except Exception:
                match = re.search(r"#(\d+)", str(e.detail))
                if match:
                    existing_id = int(match.group(1))
            if existing_id is None:
                typer.secho(
                    "--force set but could not parse existing_variant.id from 409 body.",
                    fg=typer.colors.RED,
                )
                raise typer.Exit(2)
            typer.secho(
                f"--force: deleting existing variant #{existing_id} and regenerating...",
                fg=typer.colors.YELLOW,
            )
            client._delete(
                f"/reports/{slug}/variants/{existing_id}/",
                params={"delete_generated": "true"},
            )
            data = _do_generate()
        elif e.status_code == 409:
            typer.secho("Duplicate variant — delete the existing one first, or rerun with --force.", fg=typer.colors.RED)
            typer.echo(e.detail)
            raise typer.Exit(2)
        elif e.status_code == 400:
            typer.secho("Preflight failed.", fg=typer.colors.RED, bold=True)
            typer.echo(e.detail)
            raise typer.Exit(1)
        else:
            raise

    variant_id = data.get("id")
    typer.secho(
        f"Variant #{variant_id} kicked off (status={data.get('status', '?')})",
        fg=typer.colors.GREEN,
    )

    if no_wait:
        emit(data)
        return

    # Poll the variant detail until it lands on a terminal status. Each GET
    # also triggers the backend's self-healing pass, so even if the worker
    # writes the final status late the CLI converges in O(seconds).
    typer.echo(f"Polling variant #{variant_id} (timeout {timeout}s)...")
    deadline = _time.monotonic() + timeout
    last_status = data.get("status")
    final = data
    while True:
        if _time.monotonic() > deadline:
            typer.secho(
                f"Timeout — variant #{variant_id} still '{last_status}' after {timeout}s. "
                f"The pipeline may still be running; re-check with "
                f"`kb report variant-show {slug} {variant_id}`.",
                fg=typer.colors.YELLOW,
            )
            raise typer.Exit(2)
        resp = client._get(f"/reports/{slug}/variants/{variant_id}/")
        final = resp.json()
        last_status = final.get("status")
        if last_status in ("completed", "failed", "deleted"):
            break
        _time.sleep(1.0)

    if last_status == "completed":
        typer.secho(f"Variant #{variant_id} completed.", fg=typer.colors.GREEN)
        docs = final.get("documents") or []
        if docs:
            typer.echo("Documents:")
            for d in docs:
                url = d.get("public_download_url") or d.get("public_view_url") or f"doc#{d.get('document')}"
                typer.echo(f"  [{d.get('role')}] {d.get('document_name') or d.get('document_slug')} — {url}")
        emit(final)
        return

    if last_status == "failed":
        typer.secho(
            f"Variant #{variant_id} failed: "
            f"[{final.get('error_code', '?')}] {final.get('error_message', '')}",
            fg=typer.colors.RED,
        )
        emit(final)
        raise typer.Exit(3)

    typer.secho(f"Variant #{variant_id} ended in unexpected status {last_status!r}.",
                fg=typer.colors.YELLOW)
    emit(final)
    raise typer.Exit(2)


@app.command("variants")
def list_variants(
    slug: str = typer.Argument(..., help="Report slug"),
    filter_spec: Optional[List[str]] = typer.Option(
        None, "--filter", "-f",
        help=(
            "params.KEY=VAL (exact) or params.KEY.from=V / params.KEY.to=V (range). "
            "Repeatable."
        ),
    ),
    status_filter: Optional[str] = typer.Option(None, "--status"),
    page: int = typer.Option(1, "--page"),
    page_size: int = typer.Option(50, "--page-size"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List variants of a Report, filterable by params and status."""
    client = _require_client()
    params_list: list[tuple[str, str]] = [
        ("page", str(page)),
        ("page_size", str(page_size)),
    ]
    if status_filter:
        params_list.append(("status", status_filter))
    for f in filter_spec or []:
        if "=" not in f:
            import sys
            print(f"Error: --filter must be KEY=VAL, got {f!r}", file=sys.stderr)
            raise typer.Exit(1)
        key, value = f.split("=", 1)
        if not key.startswith("params."):
            key = f"params.{key}"
        params_list.append((key, value))

    resp = client._get(f"/reports/{slug}/variants/", params=params_list)
    data = resp.json()
    emit(
        data,
        pretty=pretty,
        columns=["id", "params", "status", "executed_at", "duration_ms", "error_code"],
        title=f"Variants of {slug}",
    )


@app.command("variant-show")
def show_variant(
    slug: str = typer.Argument(..., help="Report slug"),
    variant_id: int = typer.Argument(..., help="Variant id"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a single variant with its linked documents."""
    client = _require_client()
    resp = client._get(f"/reports/{slug}/variants/{variant_id}/")
    data = resp.json()
    emit(data, pretty=pretty, title=f"Variant #{variant_id}")


@app.command("variant-delete")
def delete_variant(
    slug: str = typer.Argument(..., help="Report slug"),
    variant_id: int = typer.Argument(..., help="Variant id"),
    delete_generated: bool = typer.Option(
        False, "--delete-generated",
        help="Also delete the Documents the pipeline produced (role=generated).",
    ),
):
    """Delete a variant. Referenced Documents are preserved."""
    client = _require_client()
    path = f"/reports/{slug}/variants/{variant_id}/"
    params = {"delete_generated": "true"} if delete_generated else None
    resp = client._delete(path, params=params)
    if resp.status_code in (200, 204):
        typer.secho(f"Variant #{variant_id} deleted.", fg=typer.colors.GREEN)
    else:
        typer.secho(f"Delete failed: {resp.text}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command("preflight")
def preflight_report(
    slug: str = typer.Argument(..., help="Report slug"),
    params: Optional[str] = typer.Option(None, "--params", help='JSON params, e.g. \'{"month":"2026-03"}\''),
):
    """Validate that a Report can be generated with the given params.

    Runs the same preflight service as ``kb pipeline preflight`` but also
    validates params against the Report's declared parameter spec (typed
    checks: required fields, numeric ranges, enum options, date formats…).
    """
    client = _require_client()
    body = {}
    if params:
        body["params"] = _parse_json(params, "params")

    data = client.post(f"reports/{slug}/preflight", body)
    from ._preflight_render import render_preflight
    render_preflight(data, slug=slug, ready_verb="generate")
