"""kb browser — drive the per-session Playwright browser.

Deliberate asymmetry: every other ``kb <provider>`` subcommand routes
through ``POST /api/v1/providers/call/``. Browser bypasses the backend
because the Chromium process is owned by the local browser agent on
the user's own machine. Inserting Django would add pure serialization
overhead with no credential-security benefit (browser has no external
API credential to protect).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import typer

app = typer.Typer(help="Browser operations (runs via per-session browser-agent)")


def _port_file() -> Path:
    sid = os.environ.get("CLAUDE_SESSION_ID") or "default"
    return Path(f"/tmp/browser-{sid}.port")


def _port() -> int:
    pf = _port_file()
    if not pf.is_file():
        typer.echo(
            f"browser: browser-agent not running for this session (no {pf}). "
            f"The agent is spawned automatically by the runner — if you see "
            f"this, the workshop session may not have a browser channel "
            f"attached.",
            err=True,
        )
        raise typer.Exit(code=1)
    try:
        return int(pf.read_text().strip())
    except ValueError:
        typer.echo(f"browser: invalid port file {pf}", err=True)
        raise typer.Exit(code=1)


def _call(payload: dict[str, Any]) -> Any:
    port = _port()
    try:
        resp = httpx.post(
            f"http://127.0.0.1:{port}/cmd",
            json=payload,
            timeout=60.0,
        )
    except httpx.HTTPError as exc:
        typer.echo(f"browser: runner unreachable on port {port}: {exc}", err=True)
        raise typer.Exit(code=1)

    body = resp.json() if resp.content else {}
    if body.get("ok"):
        result = body.get("result")
        if result is not None:
            typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            typer.echo("ok")
        return

    message = body.get("error") or f"HTTP {resp.status_code}"
    typer.echo(f"browser: {message}", err=True)
    if screenshot := body.get("error_screenshot"):
        typer.echo(f"screenshot: {screenshot}", err=True)
    raise typer.Exit(code=1)


@app.command("navigate")
def navigate(url: str = typer.Argument(..., help="Target URL")):
    """Navigate the shared tab to URL."""
    _call({"op": "navigate", "url": url})


@app.command("click")
def click(selector: str = typer.Argument(..., help="CSS selector")):
    """Click the element matched by SELECTOR."""
    _call({"op": "click", "selector": selector})


@app.command("hover")
def hover(
    selector: str = typer.Argument(..., help="CSS selector"),
    timeout: int | None = typer.Option(None, "--timeout", help="ms before failing"),
    hold_ms: int | None = typer.Option(None, "--hold-ms", help="ms to hover"),
):
    """Hover over the element matched by SELECTOR."""
    payload: dict[str, Any] = {"op": "hover", "selector": selector}
    if timeout is not None:
        payload["timeout"] = timeout
    if hold_ms is not None:
        payload["holdMs"] = hold_ms
    _call(payload)


@app.command("type")
def type_text(
    selector: str = typer.Argument(..., help="CSS selector of input"),
    text: list[str] = typer.Argument(..., help="Text to type (joined with spaces)"),
):
    """Type TEXT into the element matched by SELECTOR."""
    _call({"op": "type", "selector": selector, "text": " ".join(text)})


@app.command("wait")
def wait(
    selector: str = typer.Argument(..., help="CSS selector"),
    timeout: int | None = typer.Option(None, "--timeout", help="ms before failing"),
):
    """Wait for SELECTOR to appear."""
    payload: dict[str, Any] = {"op": "wait", "selector": selector}
    if timeout is not None:
        payload["timeout"] = timeout
    _call(payload)


@app.command("read")
def read(
    selector: str = typer.Argument(..., help="CSS selector"),
    html: bool = typer.Option(False, "--html", help="Return innerHTML instead of text"),
    all_: bool = typer.Option(False, "--all", help="Return matches for every element"),
):
    """Read text (or HTML) from SELECTOR."""
    _call({"op": "read", "selector": selector, "html": html, "all": all_})


@app.command("eval")
def eval_expr(expr: list[str] = typer.Argument(..., help="JS expression")):
    """Evaluate a JS expression in the page context."""
    _call({"op": "eval", "expr": " ".join(expr)})


@app.command("url")
def url_():
    """Return the current page URL."""
    _call({"op": "url"})


@app.command("screenshot")
def screenshot(
    path: str | None = typer.Argument(None, help="Output path"),
    path_flag: str | None = typer.Option(None, "--path", help="Output path (alternative)"),
    full_page: bool = typer.Option(False, "--full-page", help="Capture full page"),
):
    """Take a screenshot of the current tab."""
    payload: dict[str, Any] = {"op": "screenshot", "fullPage": full_page}
    target = path_flag or path
    if target:
        payload["path"] = target
    _call(payload)


@app.command("upload")
def upload(
    selector: str = typer.Argument(..., help="CSS selector of file input"),
    paths: list[str] = typer.Argument(..., help="File paths to upload"),
):
    """Upload files to the input matched by SELECTOR."""
    absolute = [str(Path(p).expanduser().resolve()) for p in paths]
    _call({"op": "upload", "selector": selector, "paths": absolute})
