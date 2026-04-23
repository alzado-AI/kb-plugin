"""kb template — CRUD for reusable templates and scripts consumed by agents."""

from pathlib import Path
from typing import Optional

import typer

from ..cache import cache_path_for_template
from ..client import get_client
from ..output import emit


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


app = typer.Typer(help="Template management — reusable templates and scripts for agents")


def _write_cache(slug: str, body: str, visibility: str = "org"):
    """Write template body to cache, scoped by visibility."""
    # In HTTP mode, user_id comes from the API response, not local DB
    uid = None  # org-level templates go to shared cache
    path = cache_path_for_template(slug, visibility=visibility, user_id=uid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _delete_cache(slug: str, visibility: str = "org"):
    """Remove cached template file if it exists."""
    uid = None
    path = cache_path_for_template(slug, visibility=visibility, user_id=uid)
    if path.exists():
        path.unlink()


@app.command("list")
def list_templates(
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t", help="Filter by type"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
    with_body: bool = typer.Option(
        False,
        "--with-body",
        help="Include full body (markdown de instrucciones) en la respuesta. "
             "Por default se omite porque puede ser miles de líneas por template — "
             "usar `kb template show SLUG` para leer el body de uno específico.",
    ),
):
    """List templates with optional type filter."""
    client = _require_client()
    kwargs = {"tipo": tipo}
    if with_body:
        kwargs["with_body"] = 1
    data = client.list("templates", **kwargs)

    emit(
        data,
        pretty=pretty,
        columns=["id", "slug", "name", "tipo"],
        title="Templates",
    )


_TEXT_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "text/yaml",
    "text/x-yaml",
    "application/yaml",
    "application/x-yaml",
    "application/json",
    "application/javascript",
    "text/javascript",
    "text/html",
    "text/csv",
    "text/xml",
    "application/xml",
}


@app.command("show")
def show_template(
    slug: str = typer.Argument(..., help="Template slug"),
    pretty: bool = typer.Option(False, "--pretty"),
    read_base_file: bool = typer.Option(
        False,
        "--read-base-file",
        help=(
            "Leer el contenido del base_file e incluirlo inline en el output "
            "(solo para archivos de texto: YAML, JSON, Markdown, TXT, etc.). "
            "Usar cuando el template es hybrid/binary y el scaffold completo "
            "vive en el base_file — evita que el agente improvise sin leer "
            "la estructura real. Para binarios (xlsx/docx/pdf) usar "
            "'kb template download' en su lugar."
        ),
    ),
):
    """Show a template by slug.

    Por default devuelve body (instrucciones markdown) + metadata.
    Usar --read-base-file para leer el contenido completo del base_file
    (YAML/JSON/Markdown) e incluirlo en el output sin necesidad de descargarlo.
    """
    client = _require_client()
    data = client.show("templates", slug)

    if "error" in data:
        emit(data)
        raise typer.Exit(1)

    if read_base_file:
        base = data.get("base_file_detail")
        if not base:
            import sys
            print(
                f"Template '{slug}' no tiene base_file "
                f"(content_kind={data.get('content_kind')!r}).",
                file=sys.stderr,
            )
        else:
            ct = (base.get("content_type") or "").split(";")[0].strip().lower()
            if ct in _TEXT_CONTENT_TYPES or ct.startswith("text/"):
                try:
                    content = client.read_file_text(base["id"])
                    data["base_file_content"] = content
                except Exception as exc:  # noqa: BLE001
                    import sys
                    print(
                        f"No se pudo leer el base_file: {exc}",
                        file=sys.stderr,
                    )
                    data["base_file_content"] = None
            else:
                import sys
                print(
                    f"base_file es binario (content_type={ct!r}) — "
                    "usa 'kb template download' para obtener una copia local.",
                    file=sys.stderr,
                )
                data["base_file_content"] = None

    emit(data, pretty=pretty, title=f"Template: {data.get('name', slug)}")


@app.command("download")
def download_template(
    slug: str = typer.Argument(..., help="Template slug"),
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
):
    """Download the base_file of a binary/hybrid template to a local path.

    Agents use this to get a working copy before filling in variable parts.
    The template's base_file is never modified.
    """
    client = _require_client()
    data = client.show("templates", slug)
    if "error" in data:
        emit(data)
        raise typer.Exit(1)

    base = data.get("base_file_detail")
    if not base:
        import sys
        print(
            f"Template '{slug}' has no base_file (content_kind={data.get('content_kind')}).",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    path = client.download_file(base["id"], str(output))
    emit({
        "slug": slug,
        "filename": base.get("filename"),
        "content_type": base.get("content_type"),
        "size_bytes": base.get("size_bytes"),
        "output": path,
    })


def _upload_base_file(client, path: Path) -> int:
    """Upload a binary file as a Document with parent_type='template'.
    Returns the document id. parent_id is omitted; template will reference
    the doc via its FK instead.
    """
    result = client.upload_file(str(path), parent_type="template")
    doc_id = result.get("id")
    if not doc_id:
        import sys
        print(f"Upload failed: {result}", file=sys.stderr)
        raise SystemExit(1)
    return doc_id


def _derive_content_kind(body: Optional[str], base_file_id: Optional[int]) -> str:
    has_body = bool(body and body.strip())
    has_file = base_file_id is not None
    if has_body and has_file:
        return "hybrid"
    if has_file:
        return "binary"
    return "text"


@app.command("create")
def create_template(
    slug: str = typer.Argument(..., help="Unique slug (kebab-case)"),
    name: str = typer.Option(..., "--name", "-n", help="Human-readable name"),
    tipo: str = typer.Option(..., "--tipo", "-t", help="Type (issue, spec, replicacion, agente, script, reporte, etc.)"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    body: Optional[str] = typer.Option(None, "--body", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read text body from file"),
    base_file: Optional[Path] = typer.Option(
        None, "--base-file", help="Binary template file (xlsx/docx/pdf/pptx/html/...)"
    ),
):
    """Create a new template (text, binary, or hybrid)."""
    if file:
        body = file.read_text(encoding="utf-8")

    client = _require_client()

    base_file_id: Optional[int] = None
    if base_file:
        if not base_file.is_file():
            import sys
            print(f"base-file not found: {base_file}", file=sys.stderr)
            raise typer.Exit(1)
        base_file_id = _upload_base_file(client, base_file)

    content_kind = _derive_content_kind(body, base_file_id)

    data = client.create(
        "templates", slug=slug, name=name, tipo=tipo,
        description=description, body=body,
        base_file=base_file_id, content_kind=content_kind,
    )

    vis = data.get("visibility") or "org"
    if body:
        _write_cache(slug, body, visibility=vis)

    emit(data)


@app.command("update")
def update_template(
    slug: str = typer.Argument(..., help="Template slug"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    new_slug: Optional[str] = typer.Option(
        None, "--new-slug",
        help="Rename the template slug. Caution: update any skill/agent definitions that reference the old slug.",
    ),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    body: Optional[str] = typer.Option(None, "--body", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read text body from file"),
    base_file: Optional[Path] = typer.Option(
        None, "--base-file", help="Replace binary template file"
    ),
):
    """Update an existing template."""
    if file:
        body = file.read_text(encoding="utf-8")

    client = _require_client()

    patch: dict = {
        "name": name, "tipo": tipo, "description": description, "body": body,
    }
    if new_slug:
        patch["slug"] = new_slug
    if base_file:
        if not base_file.is_file():
            import sys
            print(f"base-file not found: {base_file}", file=sys.stderr)
            raise typer.Exit(1)
        new_doc_id = _upload_base_file(client, base_file)
        patch["base_file"] = new_doc_id
        # Caller can still be text/hybrid if they pass --body; derive otherwise.
        patch["content_kind"] = "hybrid" if (body and body.strip()) else "binary"

    data = client.update("templates", slug, **patch)

    if "error" in data:
        emit(data)
        raise typer.Exit(1)

    vis = data.get("visibility") or "org"
    final_body = data.get("body")
    effective_slug = data.get("slug") or slug
    if final_body:
        # Only invalidate the old cache entry if the API confirmed the rename
        # (i.e. the returned slug matches new_slug). A 400 response can still
        # reach here as a partial dict — checking effective_slug guards against
        # stale cache writes when the rename was rejected (e.g. duplicate slug).
        if new_slug and new_slug != slug and effective_slug == new_slug:
            _delete_cache(slug, visibility=vis)
        _write_cache(effective_slug, final_body, visibility=vis)

    emit(data)


@app.command("search")
def search_template(
    keyword: str = typer.Argument(..., help="Search keyword"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Search templates by keyword."""
    client = _require_client()
    data = client.list("templates", search=keyword)

    emit(
        data,
        pretty=pretty,
        columns=["id", "slug", "name", "tipo"],
        title=f"Templates matching '{keyword}'",
    )


@app.command("delete")
def delete_template(
    slug: str = typer.Argument(..., help="Template slug"),
):
    """Delete a template by slug."""
    client = _require_client()
    data = client.delete("templates", slug)

    vis = data.get("visibility") or "org"
    _delete_cache(slug, visibility=vis)
    emit({"ok": True, "deleted": slug})


@app.command("diff")
def diff_template(
    slug: str = typer.Argument(..., help="Template slug"),
    doc_id: Optional[int] = typer.Option(
        None, "--doc-id",
        help="Document ID to compare against. Omit to auto-resolve when the "
             "template has exactly one linked document (via source_template).",
    ),
    body_override: Optional[Path] = typer.Option(
        None, "--body-override",
        help="Path to a local file whose text replaces the document's stored "
             "content for the diff. Use this to diff against a Google Doc: "
             "`kb google doc read-tabs DOC_ID > /tmp/doc.md` then pass the file.",
    ),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Compare a rendered document against the template it was spawned from.

    Output groups unified-diff hunks by the nearest markdown heading, so
    callers can quickly see which sections drifted without reading the
    raw diff line-by-line.
    """
    client = _require_client()

    params: dict = {}
    if doc_id is not None:
        params["doc_id"] = doc_id
    if body_override is not None:
        if not body_override.is_file():
            import sys
            print(f"body-override file not found: {body_override}", file=sys.stderr)
            raise typer.Exit(1)
        params["body_override"] = body_override.read_text(encoding="utf-8")

    data = client.action("templates", slug, "diff", **params)
    emit(data, pretty=pretty, title=f"Diff: {slug}")


@app.command("pull")
def pull_templates(
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Pull all templates from DB to local cache."""
    client = _require_client()
    items = client.list("templates")
    count = 0
    for item in items:
        body = item.get("body")
        if body:
            vis = item.get("visibility") or "org"
            _write_cache(item["slug"], body, visibility=vis)
            count += 1

    emit({"pulled": count, "cache_dir": str(cache_path_for_template("").parent)}, pretty=pretty)
