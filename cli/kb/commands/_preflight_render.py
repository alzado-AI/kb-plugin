"""Shared rendering of PreflightReport output for CLI commands.

Both ``kb pipeline preflight`` and ``kb report preflight`` hit the same
backend service and print the same issue list with the same color logic.
Centralizing the renderer keeps future preflight-consuming commands
(activity, skill, etc.) one import away from a consistent UX.
"""

from __future__ import annotations

import typer


def render_preflight(data: dict, *, slug: str, ready_verb: str = "run") -> None:
    """Print a PreflightReport and exit(1) if any errors.

    ``ready_verb`` is the action the user will take on success — e.g.
    ``"run"`` for pipelines, ``"generate"`` for reports. It only affects
    the success banner text.
    """
    ok = bool(data.get("ok"))
    issues = data.get("issues") or []

    if ok and not issues:
        typer.secho(
            f"preflight OK — {slug} is ready to {ready_verb}.",
            fg=typer.colors.GREEN,
        )
        return

    banner = "PREFLIGHT OK (warnings only)" if ok else "PREFLIGHT FAILED"
    color = typer.colors.YELLOW if ok else typer.colors.RED
    typer.secho(banner, fg=color, bold=True)
    for issue in issues:
        severity = issue.get("severity", "error").upper()
        code = issue.get("code", "UNKNOWN")
        sev_color = typer.colors.RED if severity == "ERROR" else typer.colors.YELLOW
        typer.secho(
            f"  [{severity}] {code}: {issue.get('message', '')}",
            fg=sev_color,
        )
        if remediation := issue.get("remediation"):
            typer.echo(f"        → {remediation}")

    if not ok:
        raise typer.Exit(1)
