"""kb credential — Per-user encrypted credential management."""

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


app = typer.Typer(help="Credential management (per-user, encrypted)")


@app.command("list")
def list_credentials(
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List credentials for the current user.

    Only metadata (provider, alias, credential_type, env_var_name) is
    returned — credential values are resolved server-side inside provider
    handlers and never exposed to the CLI caller.
    """
    client = _require_client()
    data = client.list("credentials")

    emit(
        data, pretty=pretty,
        columns=["provider", "alias", "credential_type", "env_var_name"],
        title="Credentials",
    )


@app.command("set")
def set_credential(
    provider: str = typer.Argument(..., help="Provider name (anthropic, linear, google, github, etc.)"),
    credential_type: str = typer.Option("api_key", "--type", "-t", help="Credential type"),
    value: str = typer.Option(..., "--value", "-v", help="Credential value (will be encrypted)"),
    alias: str = typer.Option(
        "default", "--alias", "-a",
        help="Account alias (e.g. 'default', 'staging', 'prod'). "
             "Use distinct aliases to configure multiple accounts of the same provider.",
    ),
    env_var: Optional[str] = typer.Option(None, "--env-var", help="Env var name (e.g., ANTHROPIC_API_KEY)"),
):
    """Set a credential for the current user.

    The value is stored encrypted in the database. It is injected as an
    environment variable when spawning a Claude Code process.
    """
    # Auto-detect env var name if not provided
    if not env_var:
        env_var = _default_env_var(provider, credential_type)

    client = _require_client()
    data = client.create(
        "credentials",
        provider=provider,
        alias=alias,
        credential_type=credential_type,
        value=value,
        env_var_name=env_var,
    )

    emit(data)


@app.command("delete")
def delete_credential(
    provider: str = typer.Argument(..., help="Provider name"),
    credential_type: Optional[str] = typer.Option(
        None, "--type", "-t",
        help="Credential type. Omit to delete ALL rows of the (provider, alias) account.",
    ),
    alias: str = typer.Option("default", "--alias", "-a"),
):
    """Delete a credential for the current user.

    Without --type, deletes all credential rows of the given (provider, alias)
    account (i.e. removes the entire account).
    """
    client = _require_client()
    if credential_type is None:
        # Whole-account delete via new endpoint
        resp = client.http.post(
            "/credentials/delete-account/",
            json={"provider": provider, "alias": alias},
        )
        emit(resp.json() if resp.status_code == 200 else {"error": resp.text})
        return
    data = client.delete("credentials", f"{provider}/{credential_type}")
    emit(data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Default env var mapping for common providers.
# Must match what each provider's config actually reads.
_ENV_VAR_MAP = {
    ("anthropic", "api_key"): "ANTHROPIC_API_KEY",
    ("linear", "api_key"): "LINEAR_API_KEY",
    ("github", "token"): "GITHUB_TOKEN",
    ("google", "token"): "GOOGLE_TOKEN_PATH",
    ("intercom", "token"): "INTERCOM_TOKEN",
    ("figma", "token"): "FIGMA_TOKEN",
    ("diio", "oauth"): "DIIO_CREDENTIALS",
    ("metabase", "url"): "METABASE_URL",
    ("metabase", "api_key"): "METABASE_API_KEY",
}


def _default_env_var(provider: str, credential_type: str) -> str:
    """Generate a default env var name."""
    key = (provider.lower(), credential_type.lower())
    if key in _ENV_VAR_MAP:
        return _ENV_VAR_MAP[key]
    return f"{provider.upper()}_{credential_type.upper()}"
