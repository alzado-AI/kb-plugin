---
name: pendientes
domain: core
tier: basic
description: "Vista consolidada y priorizada de todos los pendientes de el usuario. Sin argumentos muestra todo; con argumento de modulo (ej: /kb:pendientes accounting) filtra por modulo."
disable-model-invocation: false
---

el usuario quiere ver sus pendientes consolidados y priorizados.

## Onboarding del dominio como pendientes implicitos

Antes de listar pendientes normales, verificar el progreso de onboarding del white-label:

```bash
KB_CLI="kb"
"$KB_CLI" organization onboarding --pretty 2>/dev/null
```

Si `percent_complete < 100%`, agregar **al final** del listado de pendientes una seccion "Onboarding del dominio" con los items del checklist que estan `done: false`. Estos no son tareas Linear ni KB tasks — son items derivados del estado de configuracion del white-label (ej: "Crear al menos una LegalEntity", "Tener >=20 terms en el glosario").

Estos items son **opcionales y de baja prioridad** — el PM ya tiene el indicador via `percent_complete`. Solo listarlos como "siguiente paso sugerido para subir cobertura del dominio".

## Phase 0: Sync de Google Docs de reuniones (silencioso)

Antes de mostrar pendientes, verifica si hay action items nuevos en Google Docs de reuniones recurrentes.

1. Consulta docs de reuniones registrados: `kb doc list --tipo meeting-notes`
2. Si no hay docs registrados o el comando falla → saltar directo a Phase 1
3. Para cada doc con Doc ID en el resultado:
   - Use the active **workspace provider** to get file info for `DOC_ID` and obtain `modifiedTime`
   - Compara `modifiedTime` (ISO timestamp, ej: `2026-03-03T15:45:12.576Z`) con `last_sync` del registro (tambien ISO, ej: `2026-03-03T17:50:00Z`)
   - Si `last_sync` es null → el doc esta stale (nunca sincronizado)
   - Si `modifiedTime` > `last_sync` (comparacion lexicografica de strings ISO funciona) → el doc esta stale
4. Si ALGUN doc esta stale:
   - Construye la lista de docs stale con su doc_id, persona, y ultimo_sync
   - Para cada doc stale: lanzar `meeting-parser` con el contenido exportado del doc + metadata
   - Consolidar PARSED_MEETINGS de todos los docs
   - Lanzar `meeting-persister` con los datos consolidados (sin gate — es sync automatico de pendientes)
   - Espera a que termine antes de continuar
5. Si NINGUN doc esta stale → skip silencioso (0 overhead extra)
6. **Fallback**: Si cualquier llamada a `get_file_info` falla (MCP error, timeout, etc.), loguea un warning breve al inicio del output y continua a Phase 1. No bloquees pendientes por un fallo de sync.

## Phase 1: Pendientes

Usa el agente `mis-pendientes` (Agent tool, subagent_type="mis-pendientes") para:
1. Leer tareas pendientes via `kb todo list --pending`
2. Filtrar por ownership de el usuario
3. Priorizar por tiers (CRITICO > URGENTE > ESTRATEGICO > PROXIMO DISCOVERY > NORMAL)
4. Retornar datos estructurados (secciones `=== META ===`, `=== MODULO: X ===`)

**IMPORTANTE**: El output NO se escribe a archivo. Se retorna directamente al chat.

Lanza el agente con este prompt:

```
Genera la vista consolidada de pendientes de el usuario. Fecha actual: {fecha de hoy}.
{Si $ARGUMENTS tiene contenido: "Filtro por modulo: $ARGUMENTS. Muestra solo items de ese modulo."}
{Si $ARGUMENTS esta vacio: "Sin filtro. Muestra todos los pendientes."}
```

Si el usuario incluyo argumentos (ej: `/kb:pendientes accounting`, `/kb:pendientes contabilidad`, `/kb:pendientes CxC`), pasalos como filtro al agente. Acepta nombre en espanol o ingles.

## Phase 2: Formatear output

El agente devuelve datos estructurados (secciones `=== META ===`, `=== MODULO: X ===`), NO output formateado. Tomar los datos y renderizarlos con este template EXACTO:

```
# Pendientes — {fecha de META}

## {Nombre del modulo}

| T | Pendiente | Src | Flags |
|---|-----------|-----|-------|
| {tier} | {pendiente} | {src} | {flags} |

(repetir tabla por cada MODULO del output del agente, omitir modulos sin items)

---
`/kb:resumen` para profundizar | `/kb:matriz` para Eisenhower | `/kb:estrategia` para vista estrategica
```

Reglas de formateo:
- Una tabla markdown por modulo
- Columnas: T (1 letra), Pendiente (max 90 chars), Src, Flags
- Ordenar filas por tier dentro de cada tabla: C primero, N ultimo
- Omitir modulos sin items
- Si el agente devuelve secciones inesperadas o formato raro, mostrar el output raw del agente como fallback
