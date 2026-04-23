"""kb doc — unified document registry (external links + uploaded blobs).

After the Document/RunArtifact unification (commit 90a54d4), this command
manages BOTH:

- ``source='external'`` — references to Google Docs, Drive files, URLs.
  Created with ``kb doc register``.
- ``source='internal'`` — files uploaded to the platform's storage.
  Created with ``kb doc upload``.

The legacy ``kb file`` command was removed. Both kinds live in the same
``documents`` table and are queried with ``kb doc list`` (filterable by
``--source``).
"""

import os
from pathlib import Path
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


def _resolve_active_session_id() -> str:
    """Return the currently active Claude transcript session ID.

    Resolution order:
    1. ``$HOME/.claude/active-session-id`` — written by the runner whenever
       Claude switches transcript files (initial spawn, ``/resume``, ``/clear``).
       This survives across switches mid-session, so a doc created after a
       ``/resume`` is tagged with the resumed conversation, not the original.
    2. ``CLAUDE_SESSION_ID`` env var — fallback for processes that started
       before the runner wrote the active file (or non-runner CLI use).
    """
    home = os.environ.get("HOME") or ""
    if home:
        try:
            content = Path(home).joinpath(".claude/active-session-id").read_text().strip()
            if content:
                return content
        except (OSError, FileNotFoundError):
            pass
    return os.environ.get("CLAUDE_SESSION_ID", "")


def _resolve_session_input(raw: Optional[str]) -> str:
    """Resolve a user-provided session id to a claude_session_id string.

    The workshop file panel filters docs by ``DocumentSessionLink.session_id``,
    which is the Claude transcript ID (``Conversation.claude_session_id``), NOT
    the workspace UUID (``Conversation.uuid``) that appears in the panel URL.
    Users only see the workspace UUID in the URL — so this helper lets them
    paste either form transparently:

    - ``"active"`` → current auto-resolved session (file/env).
    - workspace UUID → looked up via ``/conversations?uuid=`` and translated
      to its current ``claude_session_id``.
    - anything else (or lookup miss) → returned as-is (assumed already a
      claude_session_id, or the caller knows what they're doing).

    Empty/None → ``""``.
    """
    if not raw:
        return ""
    raw = raw.strip()
    if not raw:
        return ""
    if raw == "active":
        return _resolve_active_session_id()
    client = get_client()
    if not client:
        return raw
    try:
        results = client.list("conversations", uuid=raw)
        if results and isinstance(results, list):
            csid = (results[0] or {}).get("claude_session_id") or ""
            if csid:
                return csid
    except Exception:
        pass
    return raw


app = typer.Typer(help="Document registry — external links and uploaded files")


@app.command("list")
def list_documents(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t"),
    source: Optional[str] = typer.Option(
        None, "--source", "-s",
        help="Filter by 'external' (links) or 'internal' (uploaded files)",
    ),
    program: Optional[str] = typer.Option(None, "--program"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type"),
    parent_id: Optional[str] = typer.Option(None, "--parent-id"),
    session: Optional[str] = typer.Option(
        None, "--session",
        help="Filter by workshop session ID. Pass 'active' to use the current "
             "Claude session.",
    ),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List registered documents (external + internal) with optional filters."""
    client = _require_client()
    session_id = _resolve_session_input(session) if session else None
    data = client.list(
        "documents",
        module=module, tipo=tipo, source=source, program=program,
        parent_type=parent_type, parent_id=parent_id,
        session_id=session_id,
    )

    emit(
        data,
        pretty=pretty,
        columns=["id", "source", "tipo", "name", "filename", "link",
                 "module", "parent_type", "parent_id"],
        title="Documents",
    )


@app.command("find")
def find_document(
    program_slug: str = typer.Option(..., "--program", help="Program slug to search"),
    search_drive: bool = typer.Option(False, "--search-drive", help="Fallback to Drive search if not in DB"),
):
    """Find a document by program. Searches DB first, optionally falls back to Drive."""
    import subprocess

    client = _require_client()
    results = client.list("documents", search=program_slug, program=program_slug)
    if results and isinstance(results, list) and len(results) > 0:
        doc = results[0]
        emit({
            "doc_id": doc.get("doc_id"),
            "link": doc.get("link"),
            "name": doc.get("name"),
            "source": "db",
            "registered": True,
        })
        return

    if not search_drive:
        emit({"doc_id": None, "source": "none", "registered": False})
        return

    # Fallback: search Drive by program title
    title = program_slug.replace("-", " ")

    try:
        result = subprocess.run(
            ["gws", "drive", "search", f"name contains '{title}' and mimeType='application/vnd.google-apps.document'", "--max-results", "1"],
            capture_output=True, text=True, timeout=30,
        )
        import json as _json
        files = _json.loads(result.stdout) if result.stdout.strip() else []
        if files and isinstance(files, list) and len(files) > 0:
            f = files[0]
            emit({
                "doc_id": f.get("id"),
                "link": f.get("webViewLink", f"https://docs.google.com/document/d/{f.get('id')}"),
                "name": f.get("name", ""),
                "source": "drive",
                "registered": False,
            })
            return
    except (subprocess.TimeoutExpired, Exception):
        pass

    emit({"doc_id": None, "source": "none", "registered": False})


@app.command("show")
def show_document(
    doc_id: int = typer.Argument(..., help="Document ID"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a document by ID."""
    client = _require_client()
    data = client.show("documents", doc_id)

    if "error" in data:
        emit(data)
        raise typer.Exit(1)
    emit(data, pretty=pretty, title=f"Document: {data.get('name', doc_id)}")


@app.command("register")
def register_document(
    name: str = typer.Argument(..., help="Document name"),
    link: str = typer.Argument(..., help="Document link/URL"),
    tipo: str = typer.Option(..., "--tipo", "-t", help="Document type (pdd, memo, meeting-notes, external)"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    program_slug: Optional[str] = typer.Option(None, "--program"),
    project_slug: Optional[str] = typer.Option(None, "--project"),
    parent_type: Optional[str] = typer.Option(
        None, "--parent-type",
        help="Canonical parent type (program, project, meeting, person, ...). "
             "NOT used for workshop session — that is now a separate link "
             "(see --no-session to opt out of auto-linking).",
    ),
    parent_id: Optional[str] = typer.Option(
        None, "--parent-id", help="Canonical parent ID (paired with --parent-type).",
    ),
    no_session: bool = typer.Option(
        False, "--no-session",
        help="Do not auto-link this doc to the active Claude session.",
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session-id",
        help="Override the auto-resolved session. Accepts either the workspace "
             "UUID (copied from the workshop URL `?session=`) or the Claude "
             "session ID directly — the CLI translates workspace UUID to the "
             "current claude_session_id automatically. Mutually exclusive with "
             "--no-session.",
    ),
    gdoc_id: Optional[str] = typer.Option(None, "--doc-id", help="Google Doc ID"),
    version: int = typer.Option(1, "--version", "-v"),
    source_template: Optional[str] = typer.Option(
        None, "--source-template",
        help="Slug of the Template this document was rendered from. Enables "
             "``kb template diff SLUG`` to auto-resolve the doc without --doc-id.",
    ),
):
    """Register a new external document (link to Google Doc, Drive file, URL).

    The canonical parent (``--program``/``--project``/``--module``/
    ``--parent-type``) is the semantic owner of the doc. Independently, if a
    Claude session is active the doc is auto-linked to it as a *context of
    appearance* so it shows up in the workshop file panel — without pisando
    the canonical parent. Pass ``--no-session`` to skip the session link.

    Duplicate detection: if a document with the same URL (or Google Doc ID)
    is already registered, the existing record is returned instead of creating
    a duplicate. The JSON output includes ``"already_existed": true`` in that
    case so callers can detect de-dup hits.
    """
    if session_id and no_session:
        typer.echo(
            "--session-id and --no-session are mutually exclusive.",
            err=True,
        )
        raise typer.Exit(2)

    client = _require_client()

    data = client.create(
        "documents",
        source="external",
        name=name, link=link, tipo=tipo,
        module=module, program=program_slug, project=project_slug,
        parent_type=parent_type, parent_id=parent_id,
        doc_id=gdoc_id, version=version,
        source_template=source_template,
    )

    # Session link — context of appearance, not parent.
    # Always attempt to link even when the doc already existed so that a
    # repeated `kb doc register` in a new session still shows up in the
    # workshop file panel.
    if not no_session and isinstance(data, dict) and data.get("id"):
        active = (
            _resolve_session_input(session_id)
            if session_id
            else _resolve_active_session_id()
        )
        if active:
            try:
                client.action(
                    "documents", data["id"], "link-session",
                    method="post", session_id=active,
                )
                data["session_id"] = active
            except Exception:
                pass

    emit(data)


@app.command("upload")
def upload_file(
    path: str = typer.Argument(..., help="Path to file to upload"),
    parent_type: Optional[str] = typer.Option(
        None, "--parent-type", "-t",
        help="Canonical parent type (program, project, meeting, ...). Optional: "
             "if omitted and a Claude session is active, the file is linked to "
             "the session. If neither parent nor session exist (headless "
             "pipelines/CI), the doc is orphan — still uploaded and share-able.",
    ),
    parent_id: Optional[str] = typer.Option(
        None, "--parent-id", "-p", help="Canonical parent ID (paired with --parent-type).",
    ),
    no_session: bool = typer.Option(
        False, "--no-session",
        help="Do not auto-link this doc to the active Claude session.",
    ),
    session_id: Optional[str] = typer.Option(
        None, "--session-id",
        help="Override the auto-resolved session. Accepts either the workspace "
             "UUID (copied from the workshop URL `?session=`) or the Claude "
             "session ID directly. Mutually exclusive with --no-session.",
    ),
    tipo: str = typer.Option("file", "--tipo", help="Document tipo (e.g. file, report, presentacion)"),
    source_template: Optional[str] = typer.Option(
        None, "--source-template",
        help="Slug of the Template this file was rendered from. Enables "
             "``kb template diff SLUG`` to auto-resolve the doc without --doc-id.",
    ),
):
    """Upload a file to the platform — creates an internal-source Document.

    The canonical parent (``--parent-type``/``--parent-id``) is optional —
    if omitted, the file has no semantic owner and only lives under the
    active Claude session. Independently, if a Claude session is active the
    doc is auto-linked to it so it shows up in the workshop file panel. Pass
    ``--no-session`` to skip the session link.

    Automatically generates a 7-day public share token and includes
    public_view_url and public_download_url in the output so callers
    can hand the URLs out without a separate ``kb doc share`` step.
    """
    if session_id and no_session:
        typer.echo(
            "--session-id and --no-session are mutually exclusive.",
            err=True,
        )
        raise typer.Exit(2)

    client = _require_client()

    # Legacy compat: drop stale `parent_type=workshop_session` callers.
    if parent_type == "workshop_session":
        parent_type = None
        parent_id = None

    if no_session:
        session_id = ""
    elif session_id:
        session_id = _resolve_session_input(session_id)
    else:
        session_id = _resolve_active_session_id()

    # Warn on likely-unintended orphan uploads (no parent AND no session
    # AND the user didn't explicitly pass --no-session). Explicit orphans
    # — headless pipelines with --no-session — proceed silently.
    if not parent_type and not session_id and not no_session:
        typer.echo(
            "Warning: no --parent-type and no active Claude session detected. "
            "Doc will be uploaded as orphan. Pass --no-session to silence, or "
            "--parent-type/--parent-id to attach to a canonical parent.",
            err=True,
        )

    upload_kwargs: dict = {"tipo": tipo}
    if parent_type:
        upload_kwargs["parent_type"] = parent_type
        if parent_id:
            upload_kwargs["parent_id"] = parent_id
    if session_id:
        upload_kwargs["session_id"] = session_id
    if source_template:
        upload_kwargs["source_template"] = source_template

    result = client.upload_file(path, **upload_kwargs)

    # Auto-generate a public share token so agents get ready-to-use URLs.
    file_id = result.get("id")
    if file_id:
        try:
            token_data = client.action("files", file_id, "share", method="post", days=7)
            domain = (
                os.environ.get("DOMAIN")
                or os.environ.get("PUBLIC_URL")
                or os.environ.get("SITE_URL")
                or ""
            ).rstrip("/")
            download_url = token_data.get("download_url")
            view_url = token_data.get("view_url")
            result["public_download_url"] = f"{domain}{download_url}" if domain and download_url else download_url
            result["public_view_url"] = f"{domain}{view_url}" if domain and view_url else view_url
        except Exception:
            result["public_download_url"] = None
            result["public_view_url"] = None

    emit(result)


@app.command("update")
def update_document(
    doc_id: int = typer.Argument(..., help="Document ID to update"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name for the document"),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t", help="New document type"),
    link: Optional[str] = typer.Option(None, "--link", "-l", help="New URL/link (external only)"),
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Module slug to assign"),
    parent_type: Optional[str] = typer.Option(None, "--parent-type", help="New canonical parent type"),
    parent_id: Optional[str] = typer.Option(None, "--parent-id", help="New canonical parent ID"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Version number"),
):
    """Update metadata of an existing document (name, tipo, link, parent, module, version).

    Works for both external (registered links) and internal (uploaded files)
    documents. Only the fields you pass are updated — the rest remain unchanged.

    Examples::

        kb doc update 76 --name "Propuesta v2"
        kb doc update 76 --tipo memo --module receivables
        kb doc update 76 --parent-type program --parent-id 12
        kb doc update 76 --link "https://docs.google.com/document/d/NEW_ID"
    """
    client = _require_client()

    patch: dict = {
        "name": name,
        "tipo": tipo,
        "link": link,
        "parent_type": parent_type,
        "parent_id": parent_id,
        "version": version,
    }
    if module is not None:
        patch["module"] = module

    # Filter out None values so we only PATCH what was explicitly provided.
    patch = {k: v for k, v in patch.items() if v is not None}

    if not patch:
        import sys
        print("No fields to update. Pass at least one option (--name, --tipo, etc.).", file=sys.stderr)
        raise SystemExit(1)

    data = client.update("documents", doc_id, **patch)

    if "error" in data:
        emit(data)
        raise typer.Exit(1)
    emit(data)


@app.command("share")
def share_document(
    doc_id: int = typer.Argument(..., help="Document ID to generate a public link for"),
    days: int = typer.Option(7, "--days", "-d", help="Days before the link expires"),
    max_downloads: Optional[int] = typer.Option(
        None, "--max-downloads", "-m",
        help="Max times the link can be used (unlimited if omitted)",
    ),
):
    """Generate a temporary public link for an internal document (no auth)."""
    client = _require_client()
    data: dict = {"days": days}
    if max_downloads is not None:
        data["max_downloads"] = max_downloads
    result = client.action("files", doc_id, "share", method="post", **data)
    emit(result)


@app.command("unshare")
def unshare_document(
    token_id: int = typer.Argument(..., help="Token ID to revoke (from 'kb doc share' output)"),
):
    """Revoke a public token (immediately invalidates the shared link)."""
    client = _require_client()
    result = client.delete("file-tokens", token_id)
    emit(result)


@app.command("delete")
def delete_document(
    doc_id: int = typer.Argument(..., help="Document ID to delete"),
):
    """Delete a document. For internal-source, also removes the stored blob."""
    client = _require_client()
    # Internal-source files use /files/ for delete (handles blob removal);
    # external-source uses /documents/.
    doc = client.show("documents", doc_id)
    if isinstance(doc, dict) and doc.get("source") == "internal":
        result = client.delete("files", doc_id)
    else:
        result = client.delete("documents", doc_id)
    emit(result)


@app.command("link-session")
def link_session_cmd(
    doc_id: int = typer.Argument(..., help="Document ID"),
    session_id: str = typer.Argument(
        ...,
        help="Session to link. Accepts workspace UUID (from the workshop URL "
             "`?session=`), Claude session ID directly, or 'active' for the "
             "currently auto-resolved session.",
    ),
):
    """Link an existing document to a Claude session (idempotent).

    Workspace UUID is translated to its current claude_session_id
    automatically. Useful to repair docs invisible in the panel because the
    CLI auto-resolver picked a stale session id.
    """
    client = _require_client()
    sid = _resolve_session_input(session_id)
    if not sid:
        typer.echo("Could not resolve session id.", err=True)
        raise typer.Exit(1)
    data = client.action(
        "documents", doc_id, "link-session", method="post", session_id=sid,
    )
    emit(data)


@app.command("unlink-session")
def unlink_session_cmd(
    doc_id: int = typer.Argument(..., help="Document ID"),
    session_id: str = typer.Argument(
        ...,
        help="Session to unlink. Accepts workspace UUID, Claude session ID, "
             "or 'active'.",
    ),
):
    """Remove the link between a document and a Claude session (idempotent)."""
    client = _require_client()
    sid = _resolve_session_input(session_id)
    if not sid:
        typer.echo("Could not resolve session id.", err=True)
        raise typer.Exit(1)
    data = client.action(
        "documents", doc_id, "unlink-session", method="post", session_id=sid,
    )
    emit(data)
