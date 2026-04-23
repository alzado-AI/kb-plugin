"""kb provider — Auto-detect providers from filesystem + credentials.

Scans two filesystem roots:

* ``tools/*/provider.md`` — legacy per-provider CLIs (microsoft, odoo,
  whatsapp). CLI runs directly on the agent's machine.
* ``backend/apps/providers/integrations/*/provider.md`` — providers
  migrated to the backend RPC dispatcher. CLI is ``kb <slug>`` and all
  ops live under ``POST /api/v1/providers/call/``.

Both sources are merged; when a slug appears in both, the backend entry
wins (the migrated version is canonical).
"""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer

from ..output import emit

app = typer.Typer(help="Provider auto-detection (filesystem + backend catalog)")

# Repo root — kb lives at tools/kb/commands/, so four parents up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TOOLS_DIR = _REPO_ROOT / "tools"
_INTEGRATIONS_DIR = _REPO_ROOT / "backend" / "apps" / "providers" / "integrations"


def _parse_provider_md(path: Path) -> dict | None:
    """Parse provider.md header to extract slug, name, category, tipo, cli, check."""
    try:
        text = path.read_text()
    except OSError:
        return None

    slug = path.parent.name

    # Parse H1: # Name — category provider
    m = re.search(r"^#\s+(.+?)\s*—\s*(.+?)\s+provider", text, re.MULTILINE)
    name = m.group(1).strip() if m else slug
    category = m.group(2).strip() if m else "unknown"

    # Parse ## Tipo: cli|mcp
    m = re.search(r"^##\s+Tipo:\s*(\S+)", text, re.MULTILINE)
    tipo = m.group(1).strip() if m else "unknown"

    # Parse ## CLI: `name` (for cli type)
    m = re.search(r"^##\s+CLI:\s*`([^`]+)`", text, re.MULTILINE)
    cli = m.group(1).strip() if m else None

    # Parse ## Check: `command`
    m = re.search(r"^##\s+Check:\s*`([^`]+)`", text, re.MULTILINE)
    check = m.group(1).strip() if m else None

    # Parse ## MCP Prefix: `prefix` (for mcp type)
    m = re.search(r"^##\s+MCP Prefix:\s*`([^`]+)`", text, re.MULTILINE)
    mcp_prefix = m.group(1).strip() if m else None

    return {
        "slug": slug,
        "name": name,
        "category": category,
        "tipo": tipo,
        "cli": cli,
        "mcp_prefix": mcp_prefix,
        "check": check,
        "definition": str(path.relative_to(_REPO_ROOT)),
    }


def _discover() -> dict[str, dict]:
    """Return ``{slug: provider_dict}`` merging both filesystem sources.

    Backend integrations win over legacy tools when both expose the same
    slug — the migrated provider is canonical.
    """
    out: dict[str, dict] = {}
    for md in sorted(_INTEGRATIONS_DIR.glob("*/provider.md")):
        parsed = _parse_provider_md(md)
        if parsed:
            out[parsed["slug"]] = parsed
    for md in sorted(_TOOLS_DIR.glob("*/provider.md")):
        parsed = _parse_provider_md(md)
        if parsed and parsed["slug"] not in out:
            out[parsed["slug"]] = parsed
    return out


def _check_installed(provider: dict) -> str:
    """Check if provider CLI is installed. Returns 'installed' or 'missing'."""
    if provider["tipo"] == "mcp":
        return "mcp"  # MCP providers can't be checked this way
    cli = provider.get("cli")
    if not cli:
        return "missing"
    if shutil.which(cli):
        return "installed"
    return "missing"


def _check_available(provider: dict) -> str:
    """Run provider's check command to verify connectivity. Returns 'available', 'error', or 'unconfigured'."""
    check_cmd = provider.get("check")
    if not check_cmd:
        return "unknown"

    if provider["tipo"] == "mcp":
        return "mcp"  # Can't run MCP checks from CLI

    try:
        result = subprocess.run(
            check_cmd, shell=True, capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return "available"
        # Check if it's a credentials issue vs other error
        stderr = (result.stderr or "").lower()
        if any(w in stderr for w in ["credential", "token", "api_key", "auth", "not configured"]):
            return "unconfigured"
        return "error"
    except subprocess.TimeoutExpired:
        return "error"
    except Exception:
        return "error"


@app.command("list")
def list_providers(
    check: bool = typer.Option(False, "--check", help="Run check commands to verify connectivity"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List providers from both backend integrations and legacy tools/."""
    providers = []
    for parsed in _discover().values():
        if category and parsed["category"] != category:
            continue
        status = _check_available(parsed) if check else _check_installed(parsed)
        providers.append({
            "slug": parsed["slug"],
            "name": parsed["name"],
            "category": parsed["category"],
            "tipo": parsed["tipo"],
            "cli": parsed["cli"] or parsed.get("mcp_prefix", ""),
            "status": status,
            "definition_path": parsed["definition"],
        })
    emit(
        providers,
        pretty=pretty,
        columns=["slug", "name", "category", "tipo", "cli", "status", "definition_path"],
        title="Providers",
    )


@app.command("accounts")
def list_accounts(
    check: bool = typer.Option(
        False, "--check",
        help="Ping each account (runs provider check with its alias exported)",
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", help="Filter by provider slug",
    ),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """List provider accounts configured for the current user.

    An account = one or more credential rows sharing the same (provider, alias).
    Use `kb credential set` with --alias to register additional accounts.
    """
    import os

    from ..client import get_client
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)

    resp = client.http.get("/credentials/accounts/")
    if resp.status_code != 200:
        import sys
        print(f"Failed to list accounts: {resp.status_code}", file=sys.stderr)
        raise SystemExit(1)

    accounts = resp.json() or []
    if provider:
        accounts = [a for a in accounts if a["provider"] == provider]

    # Enrich with check status (scans both filesystem roots)
    if check:
        defs_by_slug = _discover()
        for acc in accounts:
            pdef = defs_by_slug.get(acc["provider"])
            if not pdef:
                acc["status"] = "no-definition"
                continue
            # Temporarily export {PROVIDER}_ALIAS so credentials resolve to this account
            env_key = f"{acc['provider'].upper()}_ALIAS"
            prev = os.environ.get(env_key)
            os.environ[env_key] = acc["alias"]
            try:
                acc["status"] = _check_available(pdef)
            finally:
                if prev is None:
                    os.environ.pop(env_key, None)
                else:
                    os.environ[env_key] = prev
    else:
        for acc in accounts:
            acc["status"] = "—"

    # Flatten credential_types list for display
    for acc in accounts:
        acc["types"] = ",".join(acc.get("credential_types", []))

    emit(
        accounts,
        pretty=pretty,
        columns=["provider", "alias", "types", "status"],
        title="Provider accounts",
    )
