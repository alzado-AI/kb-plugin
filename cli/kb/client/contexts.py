"""Multi-tenant context resolution for the kb CLI.

The CLI can be pointed at different tenant backends by switching the "active
context". Each context has a name (tenant slug), a backend URL, and a session
file with access/refresh tokens.

Layout on disk:
    ~/.kb/
        config.json              # {"current": <name>, "contexts": {<name>: {"url": ...}}}
        sessions/<name>.json     # {"access_token": ..., "refresh_token": ..., "tenant_url": ...}
        session.json             # (legacy single-tenant — auto-migrated on first read)

Resolution priority for the active context name (most specific → least):

    1. --tenant flag / KB_TENANT env var
    2. ``.kb/context`` file in the current working directory or any ancestor
    3. ``config.json.current``
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

KB_DIR = Path.home() / ".kb"
CONFIG_FILE = KB_DIR / "config.json"
SESSIONS_DIR = KB_DIR / "sessions"
LEGACY_SESSION_FILE = KB_DIR / "session.json"


@dataclass(frozen=True)
class Context:
    """A resolved active context."""
    name: str
    url: str
    session_file: Path


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    """Atomic write via tmp-file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Legacy migration — one-shot on first use
# ---------------------------------------------------------------------------

def _maybe_migrate_legacy() -> None:
    """If only the legacy ~/.kb/session.json exists, promote it to a `default` context."""
    if CONFIG_FILE.exists():
        return
    if not LEGACY_SESSION_FILE.exists():
        return

    legacy = _read_json(LEGACY_SESSION_FILE)
    access = legacy.get("access_token", "")
    if not access:
        return

    api_url = os.environ.get("KB_API_URL", "")
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    default_session = {
        "access_token": access,
        "refresh_token": legacy.get("refresh_token", "") or "",
        "email": legacy.get("email", ""),
        "tenant_slug": "default",
        "tenant_url": api_url,
    }
    _write_json(SESSIONS_DIR / "default.json", default_session)
    _write_json(CONFIG_FILE, {
        "current": "default",
        "contexts": {"default": {"url": api_url}},
    })
    # Leave ~/.kb/session.json in place for a release cycle as a safety net.


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def find_local_context() -> Optional[str]:
    """Return the context name pinned by `.kb/context` file in cwd or ancestors."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        ctx_file = parent / ".kb" / "context"
        if ctx_file.is_file():
            try:
                value = ctx_file.read_text().strip()
                if value:
                    return value
            except OSError:
                continue
    return None


def get_config() -> dict:
    """Return the full config dict, triggering legacy migration if needed."""
    _maybe_migrate_legacy()
    return _read_json(CONFIG_FILE)


def save_config(config: dict) -> None:
    _write_json(CONFIG_FILE, config)


def resolve_active() -> Optional[Context]:
    """Resolve the active context. Returns None if nothing is configured."""
    config = get_config()
    contexts = config.get("contexts") or {}

    name = (
        os.environ.get("KB_TENANT")
        or find_local_context()
        or config.get("current")
    )
    if not name or name not in contexts:
        return None

    meta = contexts[name]
    return Context(
        name=name,
        url=meta.get("url", ""),
        session_file=SESSIONS_DIR / f"{name}.json",
    )


def resolve_active_url() -> Optional[str]:
    """URL to hit for the current invocation. Honors KB_API_URL / KB_BACKEND_URL."""
    explicit = os.environ.get("KB_API_URL") or os.environ.get("KB_BACKEND_URL")
    if explicit:
        return explicit
    ctx = resolve_active()
    return ctx.url if ctx else None


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

def add_context(name: str, url: str, *, make_current: bool = True) -> None:
    """Add or update a context. Optionally switch `current` to it."""
    config = get_config()
    contexts = config.setdefault("contexts", {})
    contexts[name] = {"url": url}
    if make_current or "current" not in config:
        config["current"] = name
    save_config(config)


def set_current(name: str) -> None:
    """Switch the active context. Raises KeyError if not registered."""
    config = get_config()
    if name not in (config.get("contexts") or {}):
        raise KeyError(name)
    config["current"] = name
    save_config(config)


def remove_context(name: str) -> None:
    """Delete a context entry + its session file. No-op if unknown."""
    config = get_config()
    contexts = config.get("contexts") or {}
    if name not in contexts:
        return
    del contexts[name]
    if config.get("current") == name:
        # Pick any remaining context as the fallback, or drop `current`.
        config["current"] = next(iter(contexts), None)
    save_config(config)
    clear_session(name)


def read_session(name: str) -> dict:
    """Read the session file for a given context name."""
    return _read_json(SESSIONS_DIR / f"{name}.json")


def write_session(name: str, data: dict) -> None:
    """Atomically write the session file for a given context name."""
    _write_json(SESSIONS_DIR / f"{name}.json", data)


def clear_session(name: str) -> None:
    """Delete the session file for a context. No-op if it doesn't exist."""
    f = SESSIONS_DIR / f"{name}.json"
    if f.exists():
        try:
            f.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def list_contexts() -> list[dict]:
    """Return a list of context metadata dicts, marking `current`."""
    config = get_config()
    contexts = config.get("contexts") or {}
    current = config.get("current")
    out: list[dict] = []
    for name, meta in contexts.items():
        out.append({
            "name": name,
            "url": meta.get("url", ""),
            "current": name == current,
            "has_session": (SESSIONS_DIR / f"{name}.json").exists(),
        })
    return out
