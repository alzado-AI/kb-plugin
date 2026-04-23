"""kb org-context — organizational context block for agent system prompts."""

import json as _json
from typing import Optional

import typer

from ..client import get_client

app = typer.Typer(help="Organizational context for agents")


def _require_client():
    client = get_client()
    if not client:
        import sys
        print("KB_API_URL is required.", file=sys.stderr)
        raise SystemExit(1)
    return client


def _render_prompt_block(data: dict) -> str:
    lines = []
    org = data.get("organization") or {}
    if org:
        lines.append(f"# Contexto de la organizacion: {org.get('name', '')}")
        if org.get("industry"):
            lines.append(f"Industria: {org['industry']}")
        if org.get("modelo_negocio"):
            lines.append("")
            lines.append("## Modelo de negocio")
            lines.append(org["modelo_negocio"])
        if org.get("lineas_negocio"):
            lines.append("")
            lines.append("## Lineas de negocio")
            for ln in org["lineas_negocio"]:
                nombre = ln.get("nombre", "")
                desc = ln.get("descripcion", "")
                lines.append(f"- **{nombre}**: {desc}")
        if org.get("situaciones_especiales"):
            lines.append("")
            lines.append("## Situaciones especiales")
            for s in org["situaciones_especiales"]:
                if isinstance(s, dict):
                    lines.append(f"- {s.get('titulo', '')}: {s.get('detalle', '')}")
                else:
                    lines.append(f"- {s}")

    legal = data.get("legal_entities") or []
    if legal:
        lines.append("")
        lines.append("## Sociedades del grupo")
        for le in legal:
            flag = " (default)" if le.get("is_default") else ""
            lines.append(
                f"- **{le['slug']}**: {le['name']}{flag}"
                + (f" — tax_id {le['tax_id']}" if le.get("tax_id") else "")
            )

    glossary = data.get("glossary") or []
    if glossary:
        lines.append("")
        lines.append("## Glosario")
        for t in glossary:
            aliases = t.get("aliases") or []
            alias_str = f" (aka {', '.join(aliases)})" if aliases else ""
            lines.append(
                f"- **{t['term']}**{alias_str} [{t['tipo']}] — {t.get('definicion', '')}"
            )

    rules = data.get("business_rules") or []
    if rules:
        lines.append("")
        lines.append("## Reglas de interpretacion")
        lines.append(
            "Cuando apliques una regla, citala inline como `[rule:{slug}]`."
        )
        for r in rules:
            ctx = _json.dumps(r.get("contexto") or {}, ensure_ascii=False)
            lines.append(
                f"- **[rule:{r['slug']}]** {r['name']} — "
                f"contexto={ctx}, accion={r.get('accion', '')}"
                + (f" ({r['rationale']})" if r.get("rationale") else "")
            )

    return "\n".join(lines)


@app.callback(invoke_without_command=True)
def org_context(
    ctx: typer.Context,
    module: Optional[str] = typer.Option(None, "--module", "-m"),
    query: Optional[str] = typer.Option(
        None, "--query", "-q",
        help="Semantic query — retriever returns top_k items by similarity",
    ),
    top_k: Optional[int] = typer.Option(None, "--top-k"),
    fmt: str = typer.Option(
        "prompt", "--format", "-f", help="prompt | json",
    ),
):
    """Load organizational context (profile + glossary + rules)."""
    if ctx.invoked_subcommand is not None:
        return
    client = _require_client()
    data = client.get("org-context", module=module, query=query, top_k=top_k)
    if fmt == "json":
        print(_json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(_render_prompt_block(data))
