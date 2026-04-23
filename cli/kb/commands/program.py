"""kb program — CRUD + relations for programs."""

from decimal import Decimal
from pathlib import Path
from typing import Optional

import typer

from ..client import get_client
from ..output import emit, extract_field

app = typer.Typer(help="Program management")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required. Set it to the Django backend URL.", file=sys.stderr)
        raise SystemExit(1)
    return client


def _parse_rice_dict(rice_str: str) -> dict:
    """Parse RICE string like 'R:5 I:2 C:70% E:3' into a dict for the API."""
    result = {}
    parts = rice_str.upper().replace("%", "").split()
    for part in parts:
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        try:
            if key == "R":
                result["rice_reach"] = int(val)
            elif key == "I":
                result["rice_impact"] = int(val)
            elif key == "C":
                d = Decimal(val)
                result["rice_confidence"] = str(d / 100 if d > 1 else d)
            elif key == "E":
                result["rice_effort"] = int(val)
        except (ValueError, ArithmeticError):
            pass
    return result


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command("list")
def list_programs(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    objective: Optional[str] = typer.Option(None, "--objective", "-o"),
    missing_rice: bool = typer.Option(False, "--missing-rice"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results to show"),
):
    """List programs with optional filters."""
    client = _require_client()
    data = client.list(
        "programs", module=module, estado=estado,
        objective=objective, missing_rice="true" if missing_rice else None,
    )
    if limit and isinstance(data, list):
        data = data[:limit]
    emit(data, pretty=pretty, columns=["slug", "title", "module", "estado", "checkpoint"], title="Programs")


@app.command("show")
def show_program(
    slug: str = typer.Argument(..., help="Program slug"),
    with_projects: bool = typer.Option(False, "--with-projects"),
    with_people: bool = typer.Option(False, "--with-people"),
    with_content: bool = typer.Option(False, "--with-content"),
    full: bool = typer.Option(False, "--full", help="Include everything"),
    content_summary: bool = typer.Option(False, "--content-summary", help="Like --full but truncate content bodies to 500 chars"),
    field: Optional[str] = typer.Option(None, "--field", "-F", help="Extract a specific field using dot-notation"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a single program by slug."""
    use_full = full or content_summary or (with_projects and with_people and with_content)
    client = _require_client()
    data = client.show("programs", slug, full="true" if use_full else None)

    if content_summary and "content" in data:
        for tipo, content_dict in data["content"].items():
            if isinstance(content_dict, dict) and content_dict.get("body"):
                body = content_dict["body"]
                if len(body) > 500:
                    content_dict["body"] = body[:500] + "... [truncated, use --full for complete text]"

    if field:
        data = extract_field(data, field)
    emit(data, pretty=pretty, title=f"Program: {slug}")


@app.command("create")
def create_program(
    slug: str = typer.Argument(..., help="Program slug (kebab-case)"),
    module: str = typer.Option(..., "--module", "-m", help="Module slug"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    estado: str = typer.Option("exploratorio", "--estado", "-e"),
):
    """Create a new program."""
    client = _require_client()
    data = client.create("programs", slug=slug, module=module,
                         title=title or slug.replace("-", " ").title(), estado=estado)
    emit(data)


@app.command("update")
def update_program(
    slug: str = typer.Argument(..., help="Program slug"),
    new_slug: Optional[str] = typer.Option(
        None, "--new-slug",
        help="Rename the program slug. Caution: update any references (docs, issues) that use the old slug.",
    ),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    checkpoint: Optional[str] = typer.Option(None, "--checkpoint", "-c"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    rice: Optional[str] = typer.Option(None, "--rice", help='RICE string: "R:5 I:2 C:70% E:3"'),
    confianza: Optional[str] = typer.Option(None, "--confianza"),
    folder_path: Optional[str] = typer.Option(None, "--folder-path"),
    estacion: Optional[str] = typer.Option(None, "--estacion"),
    sub_posicion: Optional[str] = typer.Option(None, "--sub-posicion"),
    bloqueado: Optional[bool] = typer.Option(None, "--bloqueado"),
):
    """Update a program's metadata.

    To rename the program slug (with full path migration), use --new-slug.
    Internally this calls the /rename/ action which migrates workspace_path and
    folder_path atomically — equivalent to running `kb program rename`.
    """
    client = _require_client()
    if new_slug:
        # Delegate to the /rename/ action which handles path migration atomically.
        data = client.action("programs", slug, "rename", new_slug=new_slug)
        emit(data)
        return
    fields = dict(estado=estado, checkpoint=checkpoint, title=title,
                   confianza=confianza, folder_path=folder_path,
                   estacion=estacion, sub_posicion=sub_posicion, bloqueado=bloqueado)
    if rice:
        fields.update(_parse_rice_dict(rice))
    data = client.update("programs", slug, **fields)
    emit(data)


@app.command("link-need")
def link_need(
    program_slug: str = typer.Argument(..., help="Program slug"),
    need_slug: str = typer.Argument(..., help="Need slug"),
):
    """Link a program to a need (M2M)."""
    client = _require_client()
    data = client.action("programs", program_slug, "link-need", need_slug=need_slug)
    emit(data)


@app.command("unlink-need")
def unlink_need(
    program_slug: str = typer.Argument(..., help="Program slug"),
    need_slug: str = typer.Argument(..., help="Need slug"),
):
    """Unlink a program from a need."""
    client = _require_client()
    data = client.action_nested("programs", program_slug, "link-need", need_slug)
    emit(data)


@app.command("link-objective")
def link_objective(
    program_slug: str = typer.Argument(..., help="Program slug"),
    objective_id: int = typer.Argument(..., help="Objective ID"),
):
    """Link a program to an objective (M2M)."""
    client = _require_client()
    data = client.action("programs", program_slug, "link-objective", objective_id=objective_id)
    emit(data)


@app.command("unlink-objective")
def unlink_objective(
    program_slug: str = typer.Argument(..., help="Program slug"),
    objective_id: int = typer.Argument(..., help="Objective ID"),
):
    """Unlink a program from an objective."""
    client = _require_client()
    data = client.action_nested("programs", program_slug, "link-objective", objective_id)
    emit(data)


@app.command("link-project")
def link_project(
    program_slug: str = typer.Argument(..., help="Program slug"),
    project_slug: str = typer.Argument(..., help="Project slug"),
    tipo: str = typer.Option("owner", "--type", "-t", help="owner | referenced"),
    relevancia: Optional[str] = typer.Option(None, "--relevancia", "-r"),
):
    """Link a project to a program."""
    client = _require_client()
    data = client.action("programs", program_slug, "link-project",
                         project_slug=project_slug, tipo=tipo, relevancia=relevancia)
    emit(data)


@app.command("link-person")
def link_person(
    program_slug: str = typer.Argument(..., help="Program slug"),
    email: str = typer.Argument(..., help="Person email"),
    rol: str = typer.Option(..., "--rol", "-r", help="Role in this program"),
):
    """Link a person to a program."""
    client = _require_client()
    data = client.action("programs", program_slug, "link-person", email=email, rol=rol)
    emit(data)


@app.command("set-content")
def set_content(
    program_slug: str = typer.Argument(..., help="Program slug"),
    tipo: str = typer.Option(..., "--tipo", "-t", help="Content type: negocio, tecnica, etc."),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Markdown content"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Read content from file"),
):
    """Set or update content for a program."""

    if not body and not file:
        emit({"error": "Provide --body or --file"})
        raise typer.Exit(1)

    if file:
        body = file.read_text(encoding="utf-8")

    client = _require_client()
    data = client.action("programs", program_slug, "content",
                         tipo=tipo, body=body)
    emit(data)


@app.command("link-program")
def link_program(
    source_slug: str = typer.Argument(..., help="Source program slug"),
    target_slug: str = typer.Argument(..., help="Target program slug"),
    tipo: str = typer.Option(..., "--type", "-t", help="upstream | downstream | relacionado"),
    detalle: Optional[str] = typer.Option(None, "--detalle", "-d"),
):
    """Create a relation between two programs."""
    client = _require_client()
    data = client.action("programs", source_slug, "link-program",
                         target_slug=target_slug, tipo=tipo, detalle=detalle)
    emit(data)


@app.command("add-readiness")
def add_readiness(
    program_slug: str = typer.Argument(..., help="Program slug"),
    bloque: str = typer.Option(..., "--bloque", "-b", help="Block name"),
    texto: str = typer.Option(..., "--texto", "-t", help="Readiness item text"),
    sort_order: int = typer.Option(0, "--sort-order", "-s"),
):
    """Add a readiness checklist item to a program."""
    client = _require_client()
    data = client.action("programs", program_slug, "add-readiness",
                         bloque=bloque, texto=texto, sort_order=sort_order)
    emit(data)


@app.command("complete-readiness")
def complete_readiness(
    item_id: int = typer.Argument(..., help="Readiness item ID"),
):
    """Mark a readiness item as completed."""
    from datetime import date as date_type
    client = _require_client()
    data = client.update("readiness-items", item_id, completed=True,
                         completed_date=date_type.today().isoformat())
    emit(data)


@app.command("add-historial")
def add_historial(
    program_slug: str = typer.Argument(..., help="Program slug"),
    texto: str = typer.Option(..., "--texto", "-t", help="Historial entry text"),
    fecha: Optional[str] = typer.Option(None, "--fecha", "-f", help="Date (YYYY-MM-DD), defaults to today"),
):
    """Add a historial entry to a program."""
    from datetime import date as date_type
    entry_date = date_type.fromisoformat(fecha) if fecha else date_type.today()

    client = _require_client()
    data = client.action("programs", program_slug, "add-historial",
                         texto=texto, fecha=entry_date.isoformat())
    emit(data)


@app.command("rename")
def rename_program(
    old_slug: str = typer.Argument(..., help="Current program slug"),
    new_slug: str = typer.Argument(..., help="New program slug (kebab-case)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Rename a program slug with transactional FK migration.

    Updates the program slug and rewrites workspace_path / folder_path on the
    program and all linked projects that embed the old slug in their path.
    All changes are atomic — nothing is left in a partial state on failure.

    Example:
        kb program rename agentes-ia-finanzas motor-workflows
    """
    client = _require_client()

    # Preview: fetch current program to show what will change.
    try:
        program = client.show("programs", old_slug)
    except Exception as exc:
        import sys
        print(f"Error: no se encontró el program '{old_slug}'. {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(f"\nRenombrar program:")
    print(f"  slug:           {old_slug!r}  →  {new_slug!r}")

    # Show path fields that will be rewritten.
    for field in ("workspace_path", "folder_path"):
        value = program.get(field)
        if value and old_slug in value:
            print(f"  {field}: {value!r}  →  {value.replace(old_slug, new_slug)!r}")

    print()

    if not yes:
        confirm = typer.confirm("¿Confirmar renombre?", default=False)
        if not confirm:
            print("Operación cancelada.")
            raise typer.Exit()

    data = client.action("programs", old_slug, "rename", new_slug=new_slug)
    emit(data)


@app.command("delete")
def delete_program(
    slug: str = typer.Argument(..., help="Program slug"),
):
    """Delete a program (only if it has no projects or content)."""
    client = _require_client()
    data = client.delete("programs", slug)
    emit(data)
