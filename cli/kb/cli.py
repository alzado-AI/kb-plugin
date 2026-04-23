"""KB CLI — Entry point for the knowledge base CLI."""

import os
import sys

import typer

from .client import contexts, get_client, set_api_url_override
from .client.http import APIError
from .output import emit_json

from .commands import (
    infra, program, project, person, todo, query, sync, lint,
    meeting, question, document, learning, team, context, company,
    objective, search as search_cmd, gate, espera, content,
    issue, conversation, need, module,
    script, template, feedback, notification,
    view as view_cmd,
    report as report_cmd,
    # BI
    dashboard, card,
    auth, user, group, credential, provider,
    access, comment,
    agent,
    skill,
    approval,
    pipeline,
    activity,
    # White-label foundation
    entity_state,
    organization, legal_entity, term, rule, org_context,
    position, process, provider_mapping, site, zone, unit,
    industry_pack, smoke_test, conflict, drift,
    # Domain pack: comercial
    opportunity, account_plan, sales_goal,
    interaction, invoice, contract, product, line_item,
    # Domain pack: finanzas
    budget, cashflow, compliance,
    # Backward compat: action.py still exists for transition
    action,
    # Provider integrations — backend-owned outbound calls
    browser as browser_cmd,
    providers_dynamic,
)

app = typer.Typer(
    name="kb",
    help="Knowledge Base CLI — PostgreSQL-backed, multi-domain.",
    no_args_is_help=True,
)


@app.callback()
def _root(
    api_url: str = typer.Option(
        None,
        "--api-url",
        help="Override KB_API_URL for this invocation (e.g. target a different backend).",
        envvar="KB_API_URL_OVERRIDE",
    ),
    tenant: str = typer.Option(
        None,
        "--tenant",
        "-t",
        help="Force a specific tenant context for this invocation (overrides config).",
    ),
):
    """Root callback — fires before any subcommand."""
    if tenant:
        os.environ["KB_TENANT"] = tenant
    if api_url:
        set_api_url_override(api_url)
    elif not os.environ.get("KB_API_URL"):
        # Auto-populate KB_API_URL from the active context so downstream
        # code that reads the env var keeps working without per-command setup.
        active_url = contexts.resolve_active_url()
        if active_url:
            os.environ["KB_API_URL"] = active_url


# Infrastructure (top-level)
app.command("status")(infra.status)

# White-label foundation
app.add_typer(organization.app, name="organization")
app.add_typer(legal_entity.app, name="legal-entity")
app.add_typer(term.app, name="term")
app.add_typer(rule.app, name="rule")
app.add_typer(org_context.app, name="org-context")
app.add_typer(position.app, name="position")
app.add_typer(process.app, name="process")
app.add_typer(provider_mapping.app, name="provider-mapping")
app.add_typer(site.app, name="site")
app.add_typer(zone.app, name="zone")
app.add_typer(unit.app, name="unit")
app.add_typer(industry_pack.app, name="industry-pack")
app.add_typer(smoke_test.app, name="smoke-test")
app.add_typer(conflict.app, name="conflict")
app.add_typer(drift.app, name="drift")
app.add_typer(entity_state.app, name="entity-state")

# Sub-commands (new names)
app.add_typer(program.app, name="program")
app.add_typer(project.app, name="project")
app.add_typer(person.app, name="person")
app.add_typer(todo.app, name="todo")
app.add_typer(todo.app, name="task", hidden=True)  # backward compat
app.add_typer(action.app, name="action", hidden=True)  # backward compat
app.add_typer(query.app, name="query")
app.add_typer(meeting.app, name="meeting")
app.add_typer(question.app, name="question")
app.add_typer(document.app, name="doc")
app.add_typer(report_cmd.app, name="report")
app.add_typer(view_cmd.app, name="view", hidden=True)  # deprecated alias → kb report
app.add_typer(learning.app, name="learning")
app.add_typer(team.app, name="team")
app.add_typer(context.app, name="context")
app.add_typer(company.app, name="company")
app.add_typer(objective.app, name="objective")
app.add_typer(need.app, name="need")
app.add_typer(module.app, name="module")
app.add_typer(gate.app, name="gate")
app.add_typer(espera.app, name="espera")
app.add_typer(content.app, name="content")
app.add_typer(issue.app, name="issue")
app.add_typer(conversation.app, name="conversation")
app.add_typer(script.app, name="script")
app.add_typer(template.app, name="template")
app.add_typer(feedback.app, name="feedback")
app.add_typer(notification.app, name="notification")

# BI area
app.add_typer(dashboard.app, name="dashboard")
app.add_typer(card.app, name="card")

# CRM area
app.add_typer(opportunity.app, name="opportunity")
app.add_typer(account_plan.app, name="account-plan")
app.add_typer(sales_goal.app, name="sales-goal")
app.add_typer(interaction.app, name="interaction")
app.add_typer(invoice.app, name="invoice")
app.add_typer(contract.app, name="contract")
app.add_typer(product.app, name="product")
app.add_typer(line_item.app, name="line-item")

# Domain pack: finanzas
app.add_typer(budget.app, name="budget")
app.add_typer(cashflow.app, name="cashflow")
app.add_typer(compliance.app, name="compliance")

# Agent workforce
app.add_typer(agent.app, name="agent")
app.add_typer(skill.app, name="skill")
app.add_typer(approval.app, name="approval")
app.add_typer(pipeline.app, name="pipeline")
app.add_typer(activity.app, name="activity")

# Access control
app.add_typer(auth.app, name="auth")
app.add_typer(user.app, name="user")
app.add_typer(group.app, name="group")
app.add_typer(credential.app, name="credential")
app.add_typer(provider.app, name="provider")
app.add_typer(access.app, name="access")
app.add_typer(comment.app, name="comment")

# Search (top-level)
app.command("search")(search_cmd.search)

# Lint/heal
app.add_typer(lint.app, name="lint")

# Sync (replaces legacy import/export)
app.add_typer(sync.app, name="sync")

# Browser — runner-direct subcommand (bypasses Django by design, see docstring)
app.add_typer(browser_cmd.app, name="browser")

# Provider operations — generated at runtime from /providers/catalog/.
# Silent no-op if the backend is unreachable; other kb commands still work.
providers_dynamic.install_provider_commands(app)


def _humanize_api_error(err: APIError) -> dict:
    """Map an APIError to a structured JSON payload with a human hint.

    Agents consume the JSON ``code`` field programmatically; humans read
    the ``error`` line. No traceback ever reaches the terminal — that's
    reserved for actual CLI bugs, not normal 401/403/429 conditions.
    """
    client = get_client()
    source = client.token_source if client else "none"
    status = err.status_code

    if status == 401:
        hint = err.hint or {
            "session_file": "Session expired. Run: kb auth login -e <your-email>",
            "env": "Workshop session expired. Reload the browser tab.",
            "service_key": "KB_SERVICE_KEY is invalid.",
        }.get(source, "Session invalid. Log in again.")
        message = err.detail or "Authentication failed."
        code = err.code or "auth_failed"
    elif status == 403:
        hint = err.hint or "You don't have permission to perform this action."
        message = err.detail or "Permission denied."
        code = err.code or "permission_denied"
    elif status == 404:
        hint = err.hint or "Check the identifier or slug."
        message = err.detail or "Not found."
        code = err.code or "not_found"
    elif status == 429:
        hint = err.hint or "Retry in a few seconds."
        message = err.detail or "Rate limited."
        code = err.code or "rate_limited"
    elif status >= 500:
        hint = err.hint or "Backend is unavailable. Retry shortly."
        message = err.detail or "Internal server error."
        code = err.code or "server_error"
    else:
        hint = err.hint
        message = err.detail
        code = err.code or f"http_{status}"

    return {
        "error": message,
        "code": code,
        "hint": hint,
        "status": status,
    }


def main():
    """CLI entry point. Wraps ``app()`` so APIError never leaks a traceback.

    Register via pyproject ``[project.scripts]`` as ``kb = "kb.cli:main"``.
    """
    try:
        app()
    except APIError as err:
        emit_json(_humanize_api_error(err))
        sys.exit(1)


if __name__ == "__main__":
    main()
