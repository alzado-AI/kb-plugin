# Resolucion de Providers — Protocolo compartido

Todos los agentes que usan providers externos siguen este protocolo al iniciar.

## Procedimiento

1. `kb provider list` → obtener providers activos con category, status, definition path
2. Filtrar por category + `active == true` para cada capability que el agente necesita
3. **0 providers activos = operar solo con KB** (estado valido)
4. **1+ providers activos = `Read(definition_path)`** para obtener comandos disponibles del provider

## Reglas

- **KB CLI es exempt** — siempre presente, no es provider
- **Multiples providers por categoria** — iterar sobre todos los activos
- **NUNCA hardcodear** nombres de CLI (`linear`, `gws`, etc.) ni MCP tool names
- **Definiciones** (`backend/apps/providers/integrations/{name}/provider.md`) contienen command reference + data model + write rules
- **READ-ONLY por default** — write rules definidas en cada provider

## Auto-registro de archivos descargados

Cuando un wrapper de provider descarga un archivo a disco (ej. `kb google drive download`, `kb google drive export`, `kb google gmail download-attachment`), DEBE invocar `kb doc upload` automaticamente para registrarlo como Document interno. El comando auto-linkea el doc a la sesion activa de Claude via `document_session_links` — NO pasar `--parent-type workshop_session` (esa taxonomia se elimino; session es ahora un link aparte, no un parent). El wrapper inyecta `kb_doc_id` y `kb_doc_view_url` en su output JSON para que el agente que lo llamo pueda compartir el link inmediatamente.

**Reglas:**
- Trigger: `CLAUDE_SESSION_ID` esta en el env (i.e. corre dentro de un workshop)
- Disable: `KB_DOC_AUTO_REGISTER=0` para casos donde el archivo es efimero
- Non-fatal: si el upload falla, el comando original devuelve igual (no rompe el agente)
- Patron canonico: `backend/apps/providers/integrations/google/cli.py` `_auto_register_doc()` — replicable a `intercom`, `figma`, `diio`, etc.

Esta regla aplica a TODOS los wrappers de providers que descargan binarios. No es una capa opcional — es el contrato del sistema.

## Flujo KB → Project Tracker

Al crear/actualizar tickets: (1) KB primero (`kb issue create/update`), (2) sync al tracker activo. NUNCA escribir directamente al tracker sin KB.

## Sub-agentes

NUNCA usar `run_in_background: true` en Agent tool calls. Todos los agentes corren en foreground para solicitar permisos MCP interactivamente.
