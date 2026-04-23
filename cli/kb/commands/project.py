"""kb project — CRUD for projects."""

from pathlib import Path
from typing import Optional

import typer

from ..client import get_client
from ..output import emit, extract_field

from ._crud import register_delete

app = typer.Typer(help="Project management")


register_delete(app, "projects", label="project")

def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required. Set it to the Django backend URL.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_projects(
    program: Optional[str] = typer.Option(None, "--program", "-t"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    with_people: bool = typer.Option(False, "--with-people", help="Include linked people"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results to show"),
):
    """List projects with optional filters."""
    client = _require_client()
    data = client.list("projects", program=program, module=module, estado=estado)
    if limit and isinstance(data, list):
        data = data[:limit]
    emit(data, pretty=pretty, columns=["slug", "title", "module", "need", "estado", "checkpoint"], title="Projects")


@app.command("show")
def show_project(
    slug: str = typer.Argument(..., help="Project slug"),
    with_programs: bool = typer.Option(False, "--with-programs"),
    full: bool = typer.Option(False, "--full"),
    content_summary: bool = typer.Option(False, "--content-summary"),
    field: Optional[str] = typer.Option(None, "--field", "-F"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a single project by slug."""
    use_full = full or content_summary or with_programs
    client = _require_client()
    data = client.show("projects", slug, full="true" if use_full else None)

    if content_summary and "content" in data:
        for tipo, cd in data["content"].items():
            if isinstance(cd, dict) and cd.get("body") and len(cd["body"]) > 500:
                cd["body"] = cd["body"][:500] + "... [truncated, use --full for complete text]"

    if field:
        data = extract_field(data, field)
    emit(data, pretty=pretty, title=f"Project: {slug}")


@app.command("create")
def create_project(
    slug: str = typer.Argument(..., help="Project slug (kebab-case)"),
    program_slug: Optional[str] = typer.Option(None, "--program", "-t"),
    module_slug: Optional[str] = typer.Option(None, "--module", "-m"),
    need_slug: Optional[str] = typer.Option(None, "--need", "-j"),
    title: Optional[str] = typer.Option(None, "--title"),
    estado: str = typer.Option("exploratoria", "--estado", "-e"),
    auto_historial: bool = typer.Option(False, "--auto-historial"),
):
    """Create a new project and optionally link it to a program."""
    client = _require_client()
    data = client.create("projects", slug=slug, title=title or slug.replace("-", " ").title(),
                         estado=estado, module=module_slug, need=need_slug,
                         program=program_slug, auto_historial=auto_historial)
    emit(data)


@app.command("update")
def update_project(
    slug: str = typer.Argument(..., help="Project slug"),
    new_slug: Optional[str] = typer.Option(
        None, "--new-slug",
        help="Rename the project slug. Caution: update any references (docs, issues) that use the old slug.",
    ),
    estado: Optional[str] = typer.Option(None, "--estado", "-e"),
    checkpoint: Optional[str] = typer.Option(None, "--checkpoint", "-c"),
    title: Optional[str] = typer.Option(None, "--title"),
    module_slug: Optional[str] = typer.Option(None, "--module", "-m"),
    need_slug: Optional[str] = typer.Option(None, "--need", "-j"),
    linear_project_id: Optional[str] = typer.Option(None, "--linear-project-id"),
    linear_project_url: Optional[str] = typer.Option(None, "--linear-project-url"),
    folder_path: Optional[str] = typer.Option(None, "--folder-path"),
    estacion: Optional[str] = typer.Option(None, "--estacion"),
    sub_posicion: Optional[str] = typer.Option(None, "--sub-posicion"),
    bloqueado: Optional[bool] = typer.Option(None, "--bloqueado"),
    escala: Optional[str] = typer.Option(None, "--escala"),
    workspace_path: Optional[str] = typer.Option(None, "--workspace-path"),
):
    """Update a project's metadata.

    To rename the project slug (with full path migration), use --new-slug.
    Internally this calls the /rename/ action which migrates workspace_path and
    folder_path atomically.
    """
    client = _require_client()
    if new_slug:
        # Delegate to the /rename/ action which handles path migration atomically.
        data = client.action("projects", slug, "rename", new_slug=new_slug)
        emit(data)
        return
    data = client.update("projects", slug, estado=estado, checkpoint=checkpoint, title=title,
                         module=module_slug, need=need_slug, linear_project_id=linear_project_id,
                         linear_project_url=linear_project_url, folder_path=folder_path,
                         estacion=estacion, sub_posicion=sub_posicion, bloqueado=bloqueado,
                         escala=escala, workspace_path=workspace_path)
    emit(data)


@app.command("set-content")
def set_content(
    project_slug: str = typer.Argument(..., help="Project slug"),
    tipo: str = typer.Option(..., "--tipo", "-t"),
    body: Optional[str] = typer.Option(None, "--body", "-b"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
):
    """Set or update content for a project."""

    if not body and not file:
        emit({"error": "Provide --body or --file"})
        raise typer.Exit(1)
    if file:
        body = file.read_text(encoding="utf-8")

    client = _require_client()
    data = client.action("projects", project_slug, "content",
                         tipo=tipo, body=body)
    emit(data)


@app.command("link-person")
def link_person(
    project_slug: str = typer.Argument(..., help="Project slug"),
    email: str = typer.Argument(..., help="Person email"),
    rol: str = typer.Option(..., "--rol", "-r"),
):
    """Link a person to a project."""
    client = _require_client()
    data = client.action("projects", project_slug, "link-person", email=email, rol=rol)
    emit(data)


@app.command("add-readiness")
def add_readiness(
    project_slug: str = typer.Argument(..., help="Project slug"),
    bloque: str = typer.Option(..., "--bloque", "-b"),
    texto: str = typer.Option(..., "--texto", "-t"),
    sort_order: int = typer.Option(0, "--sort-order", "-s"),
):
    """Add a readiness checklist item to a project."""
    client = _require_client()
    data = client.action("projects", project_slug, "add-readiness",
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
    project_slug: str = typer.Argument(..., help="Project slug"),
    texto: str = typer.Option(..., "--texto", "-t"),
    fecha: Optional[str] = typer.Option(None, "--fecha", "-f"),
):
    """Add a historial entry to a project."""
    from datetime import date as date_type
    entry_date = date_type.fromisoformat(fecha) if fecha else date_type.today()
    client = _require_client()
    data = client.action("projects", project_slug, "add-historial",
                         texto=texto, fecha=entry_date.isoformat())
    emit(data)


@app.command("add-progress-entry")
def add_progress_entry(
    project_slug: str = typer.Argument(..., help="Project slug"),
    issue_id: str = typer.Option(..., "--issue-id", "-i"),
    titulo: Optional[str] = typer.Option(None, "--titulo"),
    prioridad: Optional[str] = typer.Option(None, "--prioridad"),
    status: Optional[str] = typer.Option(None, "--status"),
    pr_url: Optional[str] = typer.Option(None, "--pr-url"),
    branch: Optional[str] = typer.Option(None, "--branch"),
):
    """Add a progress entry for an issue in a project."""
    client = _require_client()
    data = client.action("projects", project_slug, "add-progress-entry",
                         issue_id=issue_id, titulo=titulo, prioridad=prioridad,
                         status=status, pr_url=pr_url, branch=branch)
    emit(data)


@app.command("update-progress-entry")
def update_progress_entry(
    progress_id: int = typer.Argument(..., help="ProgressEntry ID"),
    status: Optional[str] = typer.Option(None, "--status"),
    pr_url: Optional[str] = typer.Option(None, "--pr-url"),
    branch: Optional[str] = typer.Option(None, "--branch"),
    titulo: Optional[str] = typer.Option(None, "--titulo"),
    prioridad: Optional[str] = typer.Option(None, "--prioridad"),
):
    """Update an existing progress entry."""
    client = _require_client()
    data = client.update("progress-entries", progress_id, status=status, pr_url=pr_url,
                         branch=branch, titulo=titulo, prioridad=prioridad)
    emit(data)


@app.command("delete")
def delete_project(
    slug: str = typer.Argument(..., help="Project slug"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a project permanently.

    Shows a preview and asks for confirmation before deleting. Borrar un
    proyecto arrastra en cascada todos/questions/content/gates vinculados via
    parent_type=project,parent_id=N.
    """
    client = _require_client()

    # Preview: fetch project to show what will be deleted.
    try:
        project = client.show("projects", slug)
    except Exception as exc:
        import sys
        print(f"Error: no se encontró el proyecto '{slug}'. {exc}", file=sys.stderr)
        raise SystemExit(1)

    titulo = project.get("titulo") or project.get("name") or "—"
    estado = project.get("estado") or "—"

    print("\nEliminar proyecto:")
    print(f"  slug:   {slug!r}")
    print(f"  título: {titulo!r}")
    print(f"  estado: {estado}")
    print("\n⚠️  Esto borra en cascada: todos, questions, content, gates vinculados.\n")

    if not yes:
        if not typer.confirm("¿Confirmar eliminación?", default=False):
            print("Operación cancelada.")
            raise typer.Exit()

    data = client.delete("projects", slug)
    emit(data)
