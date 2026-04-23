"""kb sync — Bidirectional sync between local cache (~/.kb-cache/) and database via API."""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from ..cache import compute_hash, write_cache_file, cache_path_from_api
from ..client import get_client
from ..output import emit, emit_table, console

app = typer.Typer(help="Sync local cache with database")

CACHE_DIR = Path(os.environ.get("KB_CACHE_DIR", str(Path.home() / ".kb-cache")))
MANIFEST_PATH = CACHE_DIR / ".manifest.json"
HEADER_RE = re.compile(r"^<!-- kb-cache: id=(\d+) synced=(\S+) hash=(\w+) -->\n?")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_hash(body: str) -> str:
    return compute_hash(body)


def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_manifest(manifest: dict):
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def _strip_header(text: str) -> str:
    return HEADER_RE.sub("", text, count=1)


def _parse_header(file_path: Path) -> Optional[dict]:
    if not file_path.exists():
        return None
    first_line = file_path.open("r", encoding="utf-8").readline()
    m = HEADER_RE.match(first_line)
    if m:
        return {"id": int(m.group(1)), "synced": m.group(2), "hash": m.group(3)}
    return None


def _write_with_header(file_path: Path, content_id: int, body: str, synced_iso: str, body_hash: str):
    write_cache_file(file_path, content_id, body, synced_iso, body_hash)


def _cache_path_for(parent_type: str, parent_slug: str, tipo: str) -> Path:
    """Build cache path: ~/.kb-cache/{parent_type}s/{parent_slug}/{tipo}.md"""
    return cache_path_from_api(parent_type, parent_slug, tipo, cache_dir=CACHE_DIR)


def _build_cache_path(content) -> Path:
    """Build cache path from a content dict (API response) or object."""
    if isinstance(content, dict):
        pt = content.get("parent_type", "unknown")
        slug = content.get("parent_slug", str(content.get("parent_id", "unknown")))
        tipo = content.get("tipo", "unknown")
    else:
        pt = getattr(content, "parent_type", "unknown")
        slug = getattr(content, "_parent_slug", str(getattr(content, "parent_id", "unknown")))
        tipo = getattr(content, "tipo", "unknown")
    return _cache_path_for(pt, slug, tipo)


# ---------------------------------------------------------------------------
# Detect changes via API
# ---------------------------------------------------------------------------

def _detect_changes(client) -> list[dict]:
    """Compare manifest + local files + API content hashes."""
    manifest = _load_manifest()

    # Fetch all content metadata+hashes from API
    all_content = client._get("/sync/status/").json()

    changes = []
    seen_ids = set()

    for c in all_content:
        cid = str(c["content_id"])
        seen_ids.add(cid)
        cache_path = _cache_path_for(c["parent_type"], c["parent_slug"], c["tipo"])
        rel_path = str(cache_path.relative_to(CACHE_DIR))

        db_hash = c["body_hash"]
        db_updated = c["updated_at"]

        entry = manifest.get(cid)

        if entry is None:
            changes.append({
                "content_id": c["content_id"], "status": "remote-new",
                "path": rel_path, "tipo": c["tipo"],
                "parent_type": c["parent_type"], "parent_id": c["parent_id"],
            })
            continue

        manifest_hash = entry.get("hash", "")
        manifest_updated = entry.get("updated_at", "")

        if cache_path.exists():
            local_raw = cache_path.read_text(encoding="utf-8")
            local_body = _strip_header(local_raw)
            local_hash = _compute_hash(local_body)
        else:
            changes.append({
                "content_id": c["content_id"], "status": "local-deleted",
                "path": rel_path, "tipo": c["tipo"],
                "parent_type": c["parent_type"], "parent_id": c["parent_id"],
            })
            continue

        local_changed = local_hash != manifest_hash
        remote_changed = db_updated != manifest_updated

        if not local_changed and not remote_changed:
            status = "in-sync"
        elif local_changed and not remote_changed:
            status = "local-modified"
        elif not local_changed and remote_changed:
            status = "remote-modified"
        else:
            status = "conflict"

        changes.append({
            "content_id": c["content_id"], "status": status,
            "path": rel_path, "tipo": c["tipo"],
            "parent_type": c["parent_type"], "parent_id": c["parent_id"],
        })

    # Manifest entries whose content_id no longer exists in DB
    for cid, entry in manifest.items():
        if cid not in seen_ids:
            changes.append({
                "content_id": int(cid), "status": "db-deleted",
                "path": entry.get("cache_path", "unknown"),
                "tipo": entry.get("tipo", "unknown"),
            })

    return changes


def _apply_push(client, content_id: int, manifest: dict) -> str:
    """Push local file content to DB via API."""
    cid = str(content_id)
    entry = manifest.get(cid, {})
    cache_path_str = entry.get("cache_path")
    if not cache_path_str:
        return f"no cache path for {content_id}"

    cache_path = CACHE_DIR / cache_path_str
    local_raw = cache_path.read_text(encoding="utf-8")
    local_body = _strip_header(local_raw)

    # Push via API
    result = client._post("/sync/push/", json={
        "items": [{"content_id": content_id, "body": local_body}]
    }).json()

    item = result[0] if result else {}
    new_updated = item.get("updated_at", datetime.now(timezone.utc).isoformat())
    body_hash = _compute_hash(local_body)

    manifest[cid] = {
        "hash": body_hash,
        "cache_path": cache_path_str,
        "updated_at": new_updated,
        "tipo": entry.get("tipo", "unknown"),
    }
    _write_with_header(cache_path, content_id, local_body, new_updated, body_hash)
    return f"pushed {cache_path_str}"


def _apply_pull(client, content_id: int, manifest: dict) -> str:
    """Pull DB content to local file via API."""
    cid = str(content_id)

    # Pull body from API
    result = client._post("/sync/pull/", json={"content_ids": [content_id]}).json()
    if not result:
        return f"content {content_id} not found in DB"

    item = result[0]
    db_body = item.get("body", "")
    body_hash = _compute_hash(db_body)
    updated_iso = item.get("updated_at", datetime.now(timezone.utc).isoformat())

    cache_path = _cache_path_for(item["parent_type"], item["parent_slug"], item["tipo"])
    rel_path = str(cache_path.relative_to(CACHE_DIR))

    _write_with_header(cache_path, content_id, db_body, updated_iso, body_hash)

    manifest[cid] = {
        "hash": body_hash,
        "cache_path": rel_path,
        "updated_at": updated_iso,
        "tipo": item["tipo"],
    }
    return f"pulled {rel_path}"


# ---------------------------------------------------------------------------
# Public: update manifest after content push (called from other commands)
# ---------------------------------------------------------------------------

def update_manifest_after_push(content_id: int, body: str, updated_at_iso: str,
                               cache_path: Optional[Path] = None, tipo: Optional[str] = None):
    manifest = _load_manifest()
    cid = str(content_id)
    body_hash = _compute_hash(body)

    entry = manifest.get(cid, {})
    old_cache_path = entry.get("cache_path")

    manifest[cid] = {
        "hash": body_hash,
        "cache_path": old_cache_path or (str(cache_path.relative_to(CACHE_DIR)) if cache_path else None),
        "updated_at": updated_at_iso,
        "tipo": tipo or entry.get("tipo", "unknown"),
    }
    _save_manifest(manifest)

    if old_cache_path:
        local_path = CACHE_DIR / old_cache_path
        if local_path.exists():
            _write_with_header(local_path, content_id, body, updated_at_iso, body_hash)
    elif cache_path:
        _write_with_header(cache_path, content_id, body, updated_at_iso, body_hash)


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def sync_command(
    apply: bool = typer.Option(False, "--apply"),
    force_push: bool = typer.Option(False, "--force-push"),
    force_pull: bool = typer.Option(False, "--force-pull"),
    pull_only: bool = typer.Option(False, "--pull-only"),
    push_only: bool = typer.Option(False, "--push-only"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Detect and sync changes between local cache and database."""
    if force_push and force_pull:
        emit({"error": "Cannot use --force-push and --force-pull together"})
        raise typer.Exit(1)

    client = _require_client()

    changes = _detect_changes(client)

    summary = {"in_sync": 0, "local_modified": 0, "remote_modified": 0,
               "conflict": 0, "remote_new": 0, "local_deleted": 0, "db_deleted": 0}
    for c in changes:
        key = c["status"].replace("-", "_")
        summary[key] = summary.get(key, 0) + 1

    actionable = [c for c in changes if c["status"] != "in-sync"]

    if not apply and not force_push and not force_pull:
        result = {"summary": summary, "changes": actionable}
        if pretty:
            console.print("\n[bold]Sync Status[/bold]")
            for k, v in summary.items():
                if v > 0:
                    color = {"in_sync": "green", "local_modified": "yellow",
                             "remote_modified": "cyan", "conflict": "red",
                             "remote_new": "blue", "local_deleted": "magenta",
                             "db_deleted": "magenta"}.get(k, "white")
                    console.print(f"  [{color}]{k}: {v}[/{color}]")
            if actionable:
                console.print()
                emit_table(
                    ["content_id", "status", "tipo", "path"],
                    [[c["content_id"], c["status"], c["tipo"], c["path"]] for c in actionable],
                    title="Pending Changes",
                )
            else:
                console.print("\n[green]Everything in sync.[/green]")
        else:
            emit(result)
        return

    # Apply mode
    manifest = _load_manifest()
    applied = []
    skipped = []

    for c in changes:
        status = c["status"]
        cid = c["content_id"]

        if status == "in-sync":
            continue
        if pull_only and status not in ("remote-modified", "remote-new"):
            continue
        if push_only and status not in ("local-modified",):
            continue

        if status == "local-modified":
            if pull_only:
                continue
            msg = _apply_push(client, cid, manifest)
            applied.append({"content_id": cid, "action": "push", "detail": msg})

        elif status in ("remote-modified", "remote-new"):
            if push_only:
                continue
            msg = _apply_pull(client, cid, manifest)
            applied.append({"content_id": cid, "action": "pull", "detail": msg})

        elif status == "conflict":
            if force_push:
                msg = _apply_push(client, cid, manifest)
                applied.append({"content_id": cid, "action": "force-push", "detail": msg})
            elif force_pull:
                msg = _apply_pull(client, cid, manifest)
                applied.append({"content_id": cid, "action": "force-pull", "detail": msg})
            else:
                skipped.append({"content_id": cid, "status": "conflict",
                                "path": c["path"], "hint": "Use --force-push or --force-pull"})

        elif status == "local-deleted":
            skipped.append({"content_id": cid, "status": "local-deleted",
                            "path": c["path"], "hint": "Re-pull with --apply"})

        elif status == "db-deleted":
            skipped.append({"content_id": cid, "status": "db-deleted",
                            "path": c.get("path", "unknown"), "hint": "Content removed from DB"})

    _save_manifest(manifest)

    result = {"applied": applied, "skipped": skipped}
    if pretty:
        if applied:
            emit_table(
                ["content_id", "action", "detail"],
                [[a["content_id"], a["action"], a["detail"]] for a in applied],
                title="Applied Changes",
            )
        if skipped:
            emit_table(
                ["content_id", "status", "path", "hint"],
                [[s["content_id"], s["status"], s["path"], s["hint"]] for s in skipped],
                title="Skipped",
            )
        if not applied and not skipped:
            console.print("[green]Nothing to sync.[/green]")
    else:
        emit(result)
