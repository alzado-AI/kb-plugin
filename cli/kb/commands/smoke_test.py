"""kb smoke-test — domain config validation tests."""

import sys
from typing import Optional

import typer

from ..client import get_client
from ..output import emit

app = typer.Typer(help="Domain smoke tests")


def _require_client():
    client = get_client()
    if not client:
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


@app.command("list")
def list_tests(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    categoria: Optional[str] = typer.Option(None, "--categoria"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    data = client.list("smoke-tests", module=module, categoria=categoria)
    emit(
        data, pretty=pretty,
        columns=["slug", "pregunta", "categoria", "scope"],
        title="Smoke tests",
    )


@app.command("show")
def show(slug: str, pretty: bool = typer.Option(False, "--pretty", "-p")):
    client = _require_client()
    emit(client.show("smoke-tests", slug), pretty=pretty)


@app.command("create")
def create(
    slug: str = typer.Argument(...),
    pregunta: str = typer.Option(..., "--pregunta"),
    keywords: str = typer.Option(..., "--keywords", help="Comma-separated"),
    categoria: str = typer.Option("glossary", "--categoria"),
    scope: str = typer.Option("org", "--scope"),
    module: Optional[str] = typer.Option(None, "--module", "-m"),
):
    client = _require_client()
    emit(client.create(
        "smoke-tests", slug=slug, pregunta=pregunta,
        keywords_requeridos=[k.strip() for k in keywords.split(",")],
        categoria=categoria, scope=scope, module=module,
    ))


@app.command("run")
def run(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    categoria: Optional[str] = typer.Option(None, "--categoria"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    client = _require_client()
    data = client.post(
        "smoke-tests/run", data={"module": module, "categoria": categoria},
    )
    if pretty:
        print(f"Coverage: {data['passing']}/{data['total']} ({data['coverage_pct']}%)")
        print()
        for r in data["results"]:
            icon = "[OK]" if r["estado"] == "PASS" else "[FAIL]"
            print(f"{icon} {r['slug']}: {r['pregunta']}")
            if r["missing"]:
                print(f"     missing: {', '.join(r['missing'])}")
    else:
        emit(data)


@app.command("delete")
def delete(slug: str):
    client = _require_client()
    emit(client.delete("smoke-tests", slug))
