"""Cache path resolution with per-user isolation for KB content.

Path structure: ~/.kb-cache/u/{uid}/{tracks|missions}/{slug}/{tipo}.md
Templates:      ~/.kb-cache/u/{uid}/templates/{slug}.md

Also exposes I/O helpers used by sync.py and content.py so they can be
shared without circular imports:
  compute_hash(body)          → SHA-256 hex[:16]
  write_cache_file(...)       → escribe archivo con kb-cache header
  cache_path_from_api(...)    → construye Path desde parent_type/slug/tipo
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from .client import SESSION_FILE as _SESSION_FILE  # single source of truth

CACHE_ROOT = Path(os.environ.get("KB_CACHE_DIR", str(Path.home() / ".kb-cache")))


def _get_user_id() -> Optional[str]:
    """Get current user ID from session file or env."""
    raw = os.environ.get("KB_USER_CLAIMS")
    if raw:
        try:
            return json.loads(raw).get("sub")
        except (json.JSONDecodeError, TypeError):
            pass
    if _SESSION_FILE.exists():
        try:
            data = json.loads(_SESSION_FILE.read_text())
            return data.get("sub") or data.get("user_id")
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def _resolve_base(user_id: Optional[str] = None) -> Path:
    if user_id:
        return CACHE_ROOT / "u" / str(user_id)
    return CACHE_ROOT


def get_user_cache_dir() -> Path:
    uid = _get_user_id()
    return _resolve_base(uid)


def cache_path_for_content(slug: str, tipo: str, entity: str,
                           visibility: str = "org",
                           user_id: Optional[str] = None) -> Path:
    if not user_id:
        user_id = _get_user_id()
    base = _resolve_base(user_id)
    return base / entity / slug / f"{tipo}.md"


def cache_path_for_template(slug: str,
                            visibility: str = "org",
                            user_id: Optional[str] = None) -> Path:
    if not user_id:
        user_id = _get_user_id()
    base = _resolve_base(user_id)
    return base / "templates" / f"{slug}.md"


# ---------------------------------------------------------------------------
# I/O helpers — shared with sync.py and content.py
# ---------------------------------------------------------------------------

def compute_hash(body: str) -> str:
    """Compute SHA-256 hash (first 16 hex chars) of body text."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def write_cache_file(file_path: Path, content_id: int, body: str,
                     synced_iso: str, body_hash: str) -> None:
    """Write content to cache file with kb-cache header."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    header = f"<!-- kb-cache: id={content_id} synced={synced_iso} hash={body_hash} -->\n"
    file_path.write_text(header + body, encoding="utf-8")


def cache_path_from_api(parent_type: str, parent_slug: str, tipo: str,
                        cache_dir: Optional[Path] = None) -> Path:
    """Build cache path: {cache_dir}/{parent_type}s/{parent_slug}/{tipo}.md

    Uses CACHE_ROOT by default. Pass cache_dir to override (e.g. CACHE_DIR
    from sync.py when KB_CACHE_DIR env var differs at import time).
    """
    base = cache_dir if cache_dir is not None else CACHE_ROOT
    folder = f"{parent_type}s"
    return base / folder / parent_slug / f"{tipo}.md"
