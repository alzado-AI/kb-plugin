"""kb view — DEPRECATED alias for `kb report`.

Views were renamed to Reports in F2 of the reports refactor. The old model
(entity projection with manual ViewMembership rows) was replaced by
pipeline-backed Reports. Every ``kb view`` subcommand now proxies to the
equivalent ``kb report`` subcommand and prints a deprecation warning.

This shim is removed in F5.
"""

from __future__ import annotations

import sys

import typer

from . import report as _report_module


_DEPRECATION_NOTICE = (
    "⚠  `kb view` is deprecated — Views were renamed to Reports. "
    "Use `kb report` instead. This alias will be removed in a future release."
)


def _warn_once() -> None:
    typer.secho(_DEPRECATION_NOTICE, fg=typer.colors.YELLOW, err=True)


app = typer.Typer(
    help=(
        "DEPRECATED — use `kb report` instead. Proxies to the new Report commands."
    ),
    deprecated=True,
)


# Re-expose each command on the deprecated `kb view` namespace. Typer requires
# separate wrappers so the deprecation warning prints before the underlying
# command runs.


@app.callback(invoke_without_command=True)
def _root(ctx: typer.Context) -> None:
    """Print the deprecation warning once per invocation."""
    _warn_once()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


# Register each report subcommand under the view namespace so old muscle memory
# keeps working. Typer exposes ``app.registered_commands`` as a list of
# ``CommandInfo`` wrappers — re-registering is as simple as appending.
for _cmd in _report_module.app.registered_commands:
    app.registered_commands.append(_cmd)
