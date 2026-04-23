"""KB API HTTP client — used by CLI when KB_API_URL is set."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import contexts

_client: Optional["KBClient"] = None
_client_on_behalf_of: str = ""
_client_api_url: str = ""

# Legacy constant kept for backward-compat imports. Prefer ``active_session_file()``.
SESSION_FILE = contexts.LEGACY_SESSION_FILE


def active_session_file() -> Path:
    """Return the session file for the current context, or the legacy path."""
    ctx = contexts.resolve_active()
    if ctx is not None:
        return ctx.session_file
    return contexts.LEGACY_SESSION_FILE


def set_api_url_override(url: str) -> None:
    """Override ``KB_API_URL`` for the rest of this process.

    Called by the CLI callback when ``--api-url`` is passed. Also resets
    the singleton so the next ``get_client()`` rebuilds against the new
    URL instead of reusing a client bound to the previous one.
    """
    global _client, _client_api_url
    os.environ["KB_API_URL"] = url
    _client = None
    _client_api_url = url


@dataclass(frozen=True)
class _LoadedToken:
    """Where the access token came from — drives refresh persistence and
    the human-readable hint shown on 401."""
    access: str
    source: str  # "env", "service_key", "session_file", "none"


def get_client() -> Optional["KBClient"]:
    """Return a KBClient if KB_API_URL is set, else None.

    Resets the singleton if KB_ON_BEHALF_OF changes between calls
    (e.g. different pipeline steps in the same process).
    """
    global _client, _client_on_behalf_of
    api_url = os.environ.get("KB_API_URL")
    if not api_url:
        return None
    on_behalf_of = os.environ.get("KB_ON_BEHALF_OF", "")
    if _client is None or on_behalf_of != _client_on_behalf_of:
        loaded = _load_token()
        refresh_token = _load_refresh_token(loaded.source)
        _client = KBClient(
            api_url, loaded.access,
            on_behalf_of=on_behalf_of,
            refresh_token=refresh_token,
            token_source=loaded.source,
            session_file=SESSION_FILE if loaded.source == "session_file" else None,
        )
        _client_on_behalf_of = on_behalf_of
    return _client


def _load_token() -> _LoadedToken:
    """Load auth token + its origin. Priority:

    1. KB_ACCESS_TOKEN env var (injected by ws-server for browser sessions)
    2. KB_SERVICE_KEY env var (service mode, admin access)
    3. access_token from the active context's session file
    4. access_token from ~/.kb/session.json (pre-multi-tenant fallback)
    """
    access_token = os.environ.get("KB_ACCESS_TOKEN", "")
    if access_token:
        return _LoadedToken(access_token, "env")

    service_key = os.environ.get("KB_SERVICE_KEY", "")
    if service_key:
        return _LoadedToken(service_key, "service_key")

    session_file = active_session_file()
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text())
            tok = data.get("access_token", "")
            if tok:
                return _LoadedToken(tok, "session_file")
        except (json.JSONDecodeError, TypeError):
            pass

    return _LoadedToken("", "none")


def _load_refresh_token(source: str) -> str:
    """Load refresh token matching the access token origin."""
    env_refresh = os.environ.get("KB_REFRESH_TOKEN", "")
    if env_refresh:
        return env_refresh
    if source == "session_file":
        session_file = active_session_file()
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                return data.get("refresh_token", "") or ""
            except (json.JSONDecodeError, TypeError):
                pass
    return ""


def persist_session_tokens(access: str, refresh: str, session_file: Path = None) -> None:
    """Atomically write the rotated token pair to ``session_file``.

    Uses ``os.replace`` (POSIX-atomic rename) so concurrent CLI
    processes never see a half-written file. Callers that fail to
    write to disk keep the in-memory rotation; the next invocation
    will simply re-refresh.

    When ``session_file`` is omitted, the active context's session file is
    used (or the legacy ``~/.kb/session.json`` if no context is active).
    """
    target = session_file or active_session_file()
    try:
        data: dict = {}
        if target.exists():
            try:
                data = json.loads(target.read_text())
            except (json.JSONDecodeError, OSError):
                data = {}
        data["access_token"] = access
        if refresh:
            data["refresh_token"] = refresh
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        import os
        os.replace(tmp, target)
    except OSError:
        pass


from .http import KBClient  # noqa: E402

__all__ = ["get_client", "KBClient", "SESSION_FILE", "persist_session_tokens"]
