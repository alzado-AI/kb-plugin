"""kb person — CRUD for people."""

import unicodedata
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


def _strip_accents(s: str) -> str:
    """Remove diacritics for fuzzy name comparison (González -> Gonzalez)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )

from ._crud import register_delete

app = typer.Typer(help="Person management")


register_delete(app, "people", label="person")

@app.command("list")
def list_people(
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    team: Optional[str] = typer.Option(None, "--team", "-t"),
    company: Optional[str] = typer.Option(None, "--company", "-c", help="Filter by company name"),
    key_contacts: bool = typer.Option(False, "--key-contacts", "-k"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """List people with optional filters."""
    client = _require_client()
    data = client.list(
        "people",
        module=module,
        team=team,
        company=company,
        key_contacts="true" if key_contacts else None,
    )

    emit(
        data,
        pretty=pretty,
        columns=["name", "email", "rol", "area", "empresa"],
        title="People",
    )


@app.command("show")
def show_person(
    email: str = typer.Argument(..., help="Person email"),
    stakeholder_of: bool = typer.Option(False, "--stakeholder-of", help="Show all entities where this person is a stakeholder (cross-domain)"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Show a person by email. Use --stakeholder-of for cross-domain relationships."""
    client = _require_client()
    data = client.show("people", email, stakeholder_of="true" if stakeholder_of else None)

    emit(data, pretty=pretty, title=f"Person: {email}")


@app.command("create")
def create_person(
    name: str = typer.Argument(..., help="Full name"),
    email: str = typer.Argument(..., help="Email address"),
    rol: Optional[str] = typer.Option(None, "--rol", "-r"),
    nickname: Optional[str] = typer.Option(None, "--nickname", "-n"),
    empresa: str = typer.Option("Buk", "--empresa"),
    company_name: Optional[str] = typer.Option(None, "--company", help="Company name (looks up in companies table)"),
    area: Optional[str] = typer.Option(None, "--area", "-a"),
    key_contact: bool = typer.Option(False, "--key-contact", "-k"),
    metadata: Optional[str] = typer.Option(None, "--metadata", help="JSON metadata"),
    upsert: bool = typer.Option(False, "--upsert", help="Update existing person instead of failing"),
    force: bool = typer.Option(False, "--force", help="Skip fuzzy name dedup check"),
):
    """Create a new person."""
    import json as _json
    client = _require_client()
    meta_parsed = _json.loads(metadata) if metadata else None
    data = client.create(
        "people",
        name=name,
        email=email,
        rol=rol,
        nickname=nickname,
        empresa=empresa,
        company=company_name,
        area=area,
        key_contact="true" if key_contact else None,
        metadata=meta_parsed,
        upsert="true" if upsert else None,
        force="true" if force else None,
    )

    emit(data)


@app.command("update")
def update_person(
    email: str = typer.Argument(..., help="Person email"),
    name: Optional[str] = typer.Option(None, "--name"),
    rol: Optional[str] = typer.Option(None, "--rol", "-r"),
    nickname: Optional[str] = typer.Option(None, "--nickname", "-n"),
    area: Optional[str] = typer.Option(None, "--area", "-a"),
    company_name: Optional[str] = typer.Option(None, "--company", help="Company name"),
    key_contact: Optional[bool] = typer.Option(None, "--key-contact", "-k"),
    metadata: Optional[str] = typer.Option(None, "--metadata", help="JSON metadata (merges with existing)"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Free-text notes"),
):
    """Update a person's info."""
    import json as _json
    client = _require_client()
    meta_parsed = _json.loads(metadata) if metadata else None
    data = client.update(
        "people", email,
        name=name,
        rol=rol,
        nickname=nickname,
        area=area,
        company=company_name,
        key_contact=key_contact,
        metadata=meta_parsed,
        notes=notes,
    )

    emit(data)


@app.command("find")
def find_person(
    keyword: str = typer.Argument(..., help="Name keyword to search"),
    pretty: bool = typer.Option(False, "--pretty", "-p"),
):
    """Find people by name keyword (case-insensitive)."""
    client = _require_client()
    data = client.list("people", search=keyword)

    emit(
        data,
        pretty=pretty,
        columns=["name", "email", "rol", "area", "empresa"],
        title=f"People matching '{keyword}'",
    )
