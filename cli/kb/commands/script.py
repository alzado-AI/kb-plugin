"""kb script — CRUD + run/download for reusable executable scripts."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from ..client import get_client
from ..output import emit


def _require_client():
    client = get_client()
    if not client:
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


app = typer.Typer(help="Script management — reusable executable scripts stored in KB")


@app.command("list")
def list_scripts(
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Filter by module slug"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Filter by tags (comma-separated)"),
    pretty: bool = typer.Option(False, "--pretty", help="Rich table output"),
):
    """List scripts with optional filters."""
    client = _require_client()
    kwargs = {}
    if module:
        kwargs["module"] = module
    if tags:
        kwargs["tags"] = tags
    data = client.list("scripts", **kwargs)

    emit(
        data,
        pretty=pretty,
        columns=["id", "slug", "name", "interpreter", "version"],
        title="Scripts",
    )


@app.command("show")
def show_script(
    slug: str = typer.Argument(..., help="Script slug"),
    pretty: bool = typer.Option(False, "--pretty"),
):
    """Show a script by slug."""
    client = _require_client()
    data = client.show("scripts", slug)
    if "error" in data:
        emit(data)
        raise typer.Exit(1)
    emit(data, pretty=pretty, title=f"Script: {data.get('name', slug)}")


@app.command("create")
def create_script(
    slug: str = typer.Argument(..., help="Unique slug (kebab-case)"),
    name: str = typer.Option(..., "--name", "-n", help="Human-readable name"),
    file: Path = typer.Option(..., "--file", "-f", help="Script file to upload (.py, .sh, etc.)"),
    interpreter: Optional[str] = typer.Option(None, "--interpreter", "-i", help="Runtime (python3, bash, node)"),
    timeout: int = typer.Option(120, "--timeout", help="Default timeout in seconds"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Module slug"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    variables: Optional[str] = typer.Option(
        None, "--variables", help='JSON variables schema: \'{"name": {"type": "string", "required": true}}\'',
    ),
):
    """Create a new script — uploads the file and registers metadata."""
    if not file.is_file():
        print(f"File not found: {file}", file=sys.stderr)
        raise typer.Exit(1)

    client = _require_client()

    # Step 1: Create the script record (without file — we upload separately)
    payload = {
        "slug": slug,
        "name": name,
        "description": description or "",
        "interpreter": interpreter or "",
        "timeout_seconds": timeout,
    }
    if module:
        # Resolve module ID from slug
        modules = client.list("modules", slug=module)
        if modules:
            payload["module"] = modules[0]["id"]
    if tags:
        payload["tags"] = [t.strip() for t in tags.split(",")]
    if variables:
        try:
            payload["variables_schema"] = json.loads(variables)
        except json.JSONDecodeError:
            print("Invalid JSON for --variables", file=sys.stderr)
            raise typer.Exit(1)

    # We need to upload file as multipart, so use a combined create+upload approach
    # First create with placeholder file info, then upload the actual file
    payload["filename"] = file.name
    payload["file_path"] = ""  # Will be set by upload

    data = client.create("scripts", **payload)
    if "error" in data:
        emit(data)
        raise typer.Exit(1)

    # Step 2: Upload the file
    script_slug = data.get("slug", slug)
    upload_result = _upload_script_file(client, script_slug, file)
    if "error" in upload_result:
        emit(upload_result)
        raise typer.Exit(1)

    emit(upload_result)


@app.command("update")
def update_script(
    slug: str = typer.Argument(..., help="Script slug"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Replace script file"),
    interpreter: Optional[str] = typer.Option(None, "--interpreter", "-i"),
    timeout: Optional[int] = typer.Option(None, "--timeout"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    tags: Optional[str] = typer.Option(None, "--tags"),
    version: Optional[int] = typer.Option(None, "--version"),
    variables: Optional[str] = typer.Option(None, "--variables", help="JSON variables schema"),
):
    """Update an existing script."""
    client = _require_client()

    patch = {}
    if name is not None:
        patch["name"] = name
    if description is not None:
        patch["description"] = description
    if interpreter is not None:
        patch["interpreter"] = interpreter
    if timeout is not None:
        patch["timeout_seconds"] = timeout
    if version is not None:
        patch["version"] = version
    if tags is not None:
        patch["tags"] = [t.strip() for t in tags.split(",")]
    if variables is not None:
        try:
            patch["variables_schema"] = json.loads(variables)
        except json.JSONDecodeError:
            print("Invalid JSON for --variables", file=sys.stderr)
            raise typer.Exit(1)
    if module is not None:
        modules = client.list("modules", slug=module)
        if modules:
            patch["module"] = modules[0]["id"]

    if patch:
        data = client.update("scripts", slug, **patch)
        if "error" in data:
            emit(data)
            raise typer.Exit(1)

    # Upload new file if provided
    if file:
        if not file.is_file():
            print(f"File not found: {file}", file=sys.stderr)
            raise typer.Exit(1)
        data = _upload_script_file(client, slug, file)
        if "error" in data:
            emit(data)
            raise typer.Exit(1)
        emit(data)
    elif patch:
        emit(data)
    else:
        print("Nothing to update.", file=sys.stderr)


@app.command("run")
def run_script(
    slug: str = typer.Argument(..., help="Script slug"),
    var: Optional[list[str]] = typer.Option(
        None, "--var", help="Variable as key=value (repeatable)",
    ),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Override timeout"),
):
    """Execute a script by slug.

    Variables are passed as key=value pairs:
        kb script run my-script --var name=Antonio --var month=2026-03
    """
    client = _require_client()

    variables = {}
    if var:
        for v in var:
            if "=" not in v:
                print(f"Invalid variable format (expected key=value): {v}", file=sys.stderr)
                raise typer.Exit(1)
            key, value = v.split("=", 1)
            variables[key] = value

    payload = {"variables": variables}
    if timeout is not None:
        payload["timeout"] = timeout

    data = client.action("scripts", slug, "run", method="POST", **payload)
    if isinstance(data, dict) and data.get("error"):
        emit(data)
        raise typer.Exit(1)

    # Print stdout directly for pipeline-friendly output
    if isinstance(data, dict):
        stdout = data.get("stdout", "")
        stderr = data.get("stderr", "")
        rc = data.get("return_code", 0)

        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, file=sys.stderr, end="")
        if rc != 0:
            raise typer.Exit(rc)
    else:
        emit(data)


@app.command("download")
def download_script(
    slug: str = typer.Argument(..., help="Script slug"),
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
):
    """Download a script file to a local path."""
    client = _require_client()
    data = client.show("scripts", slug)
    if "error" in data:
        emit(data)
        raise typer.Exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    resp = client.http.get(f"/scripts/{slug}/download/")
    if resp.status_code >= 400:
        emit({"error": f"Download failed: {resp.status_code}"})
        raise typer.Exit(1)
    output.write_bytes(resp.content)
    emit({
        "slug": slug,
        "filename": data.get("filename"),
        "output": str(output.resolve()),
    })


@app.command("delete")
def delete_script(
    slug: str = typer.Argument(..., help="Script slug"),
):
    """Delete a script by slug."""
    client = _require_client()
    data = client.delete("scripts", slug)
    emit({"ok": True, "deleted": slug})


def _upload_script_file(client, slug: str, file: Path) -> dict:
    """Upload a script file via the /scripts/{slug}/upload/ action."""
    import httpx

    def _do_upload() -> httpx.Response:
        headers = {}
        if "Authorization" in client.http.headers:
            headers["Authorization"] = str(client.http.headers["Authorization"])
        with open(file, "rb") as f:
            return httpx.post(
                f"{str(client.http.base_url).rstrip('/')}/scripts/{slug}/upload/",
                files={"file": (file.name, f)},
                headers=headers,
                timeout=60.0,
            )

    resp = _do_upload()
    if resp.status_code == 401 and client._do_refresh():
        resp = _do_upload()

    if resp.status_code >= 400:
        return {"error": f"Upload failed: {resp.status_code} {resp.text[:200]}"}
    return resp.json()
