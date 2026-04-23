"""kb auth — authentication + multi-tenant context management.

The CLI supports multiple tenant backends via "contexts". Each context has a
name (tenant slug), a backend URL, and a session file with rotatable tokens.

Commands:
    kb auth login                Device-flow login via core (opens browser).
    kb auth login --email --password    Legacy direct login (CI/scripts).
    kb auth use <tenant>         Switch the active context.
    kb auth add-context <n> <u>  Register a tenant URL manually.
    kb auth list                 List configured contexts.
    kb auth status               Validate current session.
    kb auth logout [<tenant>]    Clear a session.
"""

from __future__ import annotations

import json
import os
import time
import webbrowser
from typing import Optional

import httpx
import typer

from ..client import active_session_file, contexts, persist_session_tokens
from ..output import emit

app = typer.Typer(help="Authentication and tenant context management")


DEFAULT_CORE_URL = "https://core.alzadi.org"
DEVICE_POLL_MAX_SECONDS = 600  # match backend's TTL


def _core_url(override: Optional[str] = None) -> str:
    """Resolve the core-hub URL for device flow. Flag > env var > default."""
    return (
        override
        or os.environ.get("KB_CORE_URL")
        or DEFAULT_CORE_URL
    )


def _load_session_tokens(session_file) -> tuple[str, str]:
    """Return ``(access, refresh)`` from the given session file, or empty."""
    if not session_file.exists():
        return "", ""
    try:
        data = json.loads(session_file.read_text())
    except (json.JSONDecodeError, TypeError):
        return "", ""
    return data.get("access_token", "") or "", data.get("refresh_token", "") or ""


def _try_refresh(api_url: str, refresh: str, session_file) -> Optional[str]:
    """Exchange a refresh token for a new access token (single attempt)."""
    if not refresh:
        return None
    try:
        resp = httpx.post(
            f"{api_url}/api/v1/auth/token/refresh/",
            json={"refresh": refresh},
            timeout=10,
        )
    except httpx.RequestError:
        return None
    if resp.status_code != 200:
        return None
    body = resp.json()
    new_access = body.get("access", "")
    new_refresh = body.get("refresh", "") or refresh
    persist_session_tokens(new_access, new_refresh, session_file)
    return new_access


# ---------------------------------------------------------------------------
# login — device flow (default) + email/password fallback
# ---------------------------------------------------------------------------

@app.command("login")
def login(
    email: Optional[str] = typer.Option(
        None, "--email", "-e",
        help="Legacy email-based login (skips device flow).",
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", hide_input=True,
        help="Legacy password-based login (skips device flow).",
    ),
    core_url: Optional[str] = typer.Option(
        None, "--core-url",
        help="Override the core hub URL (also: KB_CORE_URL env var).",
    ),
    tenant: Optional[str] = typer.Option(
        None, "--tenant",
        help="Required with --email: which tenant's backend to log in against.",
    ),
    no_browser: bool = typer.Option(
        False, "--no-browser",
        help="Don't open the browser automatically — just print the URL.",
    ),
):
    """Log in. Opens browser via device flow by default; --email/--password for CI."""

    # --- Legacy path: --email + --password → direct token-obtain ----------
    if email or password:
        if not (email and password):
            emit({"error": "--email and --password must be used together"})
            raise typer.Exit(1)
        api_url = (
            os.environ.get("KB_API_URL")
            or (contexts.resolve_active().url if contexts.resolve_active() else None)
        )
        if not api_url:
            emit({
                "error": "Need an active tenant or KB_API_URL for legacy login. "
                         "Use device flow (`kb auth login` without flags) or set --tenant."
            })
            raise typer.Exit(1)
        if tenant:
            # Add/switch context explicitly so the session ends up where the user wanted.
            contexts.add_context(tenant, api_url, make_current=True)

        try:
            resp = httpx.post(
                f"{api_url}/api/v1/auth/login/",
                json={"email": email, "password": password},
                timeout=10,
            )
        except httpx.ConnectError:
            emit({"error": f"Cannot connect to {api_url}"})
            raise typer.Exit(1)
        if resp.status_code != 200:
            emit({"error": f"Login failed: {resp.text}"})
            raise typer.Exit(1)
        tokens = resp.json()
        active = contexts.resolve_active()
        session_name = active.name if active else (tenant or "default")
        if not active:
            contexts.add_context(session_name, api_url, make_current=True)
        contexts.write_session(session_name, {
            "access_token": tokens["access"],
            "refresh_token": tokens.get("refresh", ""),
            "email": email,
            "tenant_slug": session_name,
            "tenant_url": api_url,
        })
        emit({
            "status": "ok",
            "context": session_name,
            "email": email,
            "message": "Logged in (legacy flow).",
        })
        return

    # --- Default path: device flow via core -------------------------------
    core = _core_url(core_url)
    try:
        resp = httpx.post(f"{core}/api/v1/auth/device/code/", timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        emit({"error": f"Cannot reach core at {core}: {e}"})
        raise typer.Exit(1)

    body = resp.json()
    device_code = body["device_code"]
    user_code = body["user_code"]
    verification_uri = body["verification_uri"]
    interval = int(body.get("interval", 3))
    expires_in = int(body.get("expires_in", DEVICE_POLL_MAX_SECONDS))

    typer.echo(f"\n  Abre en tu browser: {verification_uri}")
    typer.echo(f"  Y confirma el código: {user_code}\n")

    if not no_browser:
        try:
            webbrowser.open(verification_uri)
        except Exception:
            pass

    deadline = time.time() + expires_in
    cur_interval = interval
    tenant_slug = None
    tokens = None

    while time.time() < deadline:
        time.sleep(cur_interval)
        try:
            poll = httpx.post(
                f"{core}/api/v1/auth/device/token/",
                json={"device_code": device_code},
                timeout=10,
            )
        except httpx.RequestError:
            continue  # transient — try again on next tick

        if poll.status_code == 200:
            tokens = poll.json()
            tenant_slug = tokens.get("tenant_slug")
            break

        error = ""
        try:
            error = poll.json().get("error", "")
        except (ValueError, KeyError):
            pass

        if error == "authorization_pending":
            continue
        if error == "slow_down":
            cur_interval = min(cur_interval + 2, 30)
            continue
        if error in {"expired_token", "access_denied", "invalid_device_code"}:
            emit({"error": error, "message": "Reintentá `kb auth login`."})
            raise typer.Exit(1)
        # Unknown — back off and keep polling
        cur_interval = min(cur_interval + 1, 30)

    if tokens is None or tenant_slug is None:
        emit({"error": "timeout", "message": "El código expiró antes de confirmarlo."})
        raise typer.Exit(1)

    # Persist context + session
    tenant_url = tokens.get("tenant_url") or ""
    contexts.add_context(tenant_slug, tenant_url, make_current=True)
    contexts.write_session(tenant_slug, {
        "access_token": tokens["access"],
        "refresh_token": tokens.get("refresh", ""),
        "tenant_slug": tenant_slug,
        "tenant_url": tenant_url,
    })

    emit({
        "status": "ok",
        "context": tenant_slug,
        "tenant_url": tenant_url,
        "message": f"✓ conectado al tenant '{tenant_slug}'.",
    })


# ---------------------------------------------------------------------------
# use / add-context / list
# ---------------------------------------------------------------------------

@app.command("use")
def use(tenant: str = typer.Argument(..., help="Context name (tenant slug) to activate")):
    """Switch the active context."""
    try:
        contexts.set_current(tenant)
    except KeyError:
        emit({"error": f"No such context: {tenant}. Run `kb auth list` to see available."})
        raise typer.Exit(1)
    emit({"status": "ok", "current": tenant})


@app.command("add-context")
def add_context(
    name: str = typer.Argument(..., help="Context name (tenant slug)"),
    url: str = typer.Argument(..., help="Backend URL (e.g. https://buk.alzadi.org)"),
    current: bool = typer.Option(True, "--current/--no-current",
                                  help="Make this the active context (default: true)."),
):
    """Register a tenant URL manually (bypasses the browser flow)."""
    contexts.add_context(name, url, make_current=current)
    emit({"status": "ok", "name": name, "url": url, "current": current})


@app.command("list")
def list_cmd():
    """List configured contexts."""
    emit({"contexts": contexts.list_contexts()})


# ---------------------------------------------------------------------------
# status / logout
# ---------------------------------------------------------------------------

@app.command("status")
def status():
    """Show current authentication status for the active context."""
    active = contexts.resolve_active()
    api_url = os.environ.get("KB_API_URL") or (active.url if active else "")

    if not api_url:
        emit({
            "authenticated": False,
            "error": "No active context or KB_API_URL. Run `kb auth login`.",
        })
        return

    token = (
        os.environ.get("KB_ACCESS_TOKEN")
        or os.environ.get("KB_SERVICE_KEY")
        or ""
    )
    session_file = active_session_file()
    session_access, session_refresh = _load_session_tokens(session_file)
    env_refresh = os.environ.get("KB_REFRESH_TOKEN", "")
    if not token:
        token = session_access

    if not token:
        emit({
            "authenticated": False,
            "api_url": api_url,
            "context": active.name if active else None,
            "message": "No token. Run: kb auth login",
        })
        return

    def _me(tok: str):
        return httpx.get(
            f"{api_url}/api/v1/auth/me/",
            headers={"Authorization": f"Bearer {tok}"},
            timeout=10,
        )

    try:
        resp = _me(token)
        if resp.status_code == 401:
            refresh = env_refresh or session_refresh
            new_access = _try_refresh(api_url, refresh, session_file)
            if new_access:
                resp = _me(new_access)

        if resp.status_code == 200:
            user = resp.json()
            emit({
                "authenticated": True,
                "context": active.name if active else None,
                "api_url": api_url,
                "email": user.get("email"),
                "role": user.get("role"),
                "uuid": user.get("uuid"),
                "is_admin": user.get("is_admin"),
            })
        else:
            emit({
                "authenticated": False,
                "api_url": api_url,
                "context": active.name if active else None,
                "error": f"Token invalid ({resp.status_code})",
            })
    except Exception as e:
        emit({"authenticated": False, "api_url": api_url, "error": str(e)})


@app.command("logout")
def logout(
    tenant: Optional[str] = typer.Argument(
        None, help="Context to clear (default: active context)."
    ),
    all_contexts: bool = typer.Option(
        False, "--all", help="Clear sessions for every context.",
    ),
):
    """Clear stored session(s)."""
    if all_contexts:
        cleared = []
        for ctx in contexts.list_contexts():
            contexts.clear_session(ctx["name"])
            cleared.append(ctx["name"])
        emit({"status": "ok", "cleared": cleared})
        return

    name = tenant
    if not name:
        active = contexts.resolve_active()
        name = active.name if active else None
    if not name:
        emit({"status": "ok", "message": "No active session."})
        return
    contexts.clear_session(name)
    emit({"status": "ok", "cleared": name})
