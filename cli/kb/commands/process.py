"""kb process — flujos operativos del negocio."""

import json as _json
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Business processes (domain, not agent pipelines)")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_processes(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    as_of: Optional[str] = typer.Option(None, "--as-of"),
    include_history: bool = typer.Option(False, "--include-history"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    data = client.list(
        "processes", module=module, as_of=as_of,
        include_history="true" if include_history else None,
    )
    emit(
        data, pretty=pretty,
        columns=["slug", "name", "module", "trigger", "outcome", "valid_to"],
        title="Processes",
    )


@app.command("show")
def show(slug: str, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    emit(client.show("processes", slug), pretty=pretty, title=f"Process: {slug}")


@app.command("create")
def create(
    slug: str = typer.Argument(...),
    name: str = typer.Option(..., "--name"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    trigger: Optional[str] = typer.Option(None, "--trigger"),
    outcome: Optional[str] = typer.Option(None, "--outcome"),
    descripcion: Optional[str] = typer.Option(None, "--descripcion", "-d"),
):
    client = _require_client()
    emit(client.create(
        "processes",
        slug=slug, name=name, module=module,
        trigger=trigger, outcome=outcome, descripcion=descripcion,
    ))


@app.command("update")
def update(
    slug: str = typer.Argument(...),
    name: Optional[str] = typer.Option(None, "--name"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    trigger: Optional[str] = typer.Option(None, "--trigger"),
    outcome: Optional[str] = typer.Option(None, "--outcome"),
    descripcion: Optional[str] = typer.Option(None, "--descripcion", "-d"),
):
    client = _require_client()
    payload = {
        k: v for k, v in {
            "name": name, "module": module, "trigger": trigger,
            "outcome": outcome, "descripcion": descripcion,
        }.items() if v is not None
    }
    emit(client.update("processes", slug, **payload))


@app.command("add-step")
def add_step(
    slug: str = typer.Argument(...),
    nombre: str = typer.Argument(...),
    actor: Optional[str] = typer.Option(None, "--actor", help="Position slug"),
    actor_libre: Optional[str] = typer.Option(None, "--actor-libre"),
    sistema: Optional[str] = typer.Option(None, "--sistema"),
    inputs: Optional[str] = typer.Option(None, "--inputs", help="Comma-separated"),
    outputs: Optional[str] = typer.Option(None, "--outputs", help="Comma-separated"),
    handoff_to: Optional[str] = typer.Option(None, "--handoff-to"),
    orden: Optional[int] = typer.Option(None, "--orden"),
):
    client = _require_client()
    payload = {"nombre": nombre}
    if actor:
        payload["actor"] = actor
    if actor_libre:
        payload["actor_libre"] = actor_libre
    if sistema:
        payload["sistema"] = sistema
    if inputs:
        payload["inputs"] = [i.strip() for i in inputs.split(",")]
    if outputs:
        payload["outputs"] = [o.strip() for o in outputs.split(",")]
    if handoff_to:
        payload["handoff_to"] = handoff_to
    if orden is not None:
        payload["orden"] = orden
    emit(client.post(f"processes/{slug}/add-step", data=payload))


@app.command("remove-step")
def remove_step(
    slug: str = typer.Argument(...),
    step_id: int = typer.Argument(...),
):
    client = _require_client()
    emit(client.post(f"processes/{slug}/remove-step", data={"step_id": step_id}))


@app.command("reorder-steps")
def reorder_steps(
    slug: str = typer.Argument(...),
    order: str = typer.Argument(..., help="Comma-separated step ids in new order"),
):
    client = _require_client()
    ids = [int(x.strip()) for x in order.split(",")]
    emit(client.post(f"processes/{slug}/reorder-steps", data={"order": ids}))


@app.command("delete")
def delete(slug: str):
    client = _require_client()
    emit(client.delete("processes", slug))
