---
name: audit
domain: pm
description: "Comparar discovery/tecnica.md vs codigo implementado. Modos: completeness (que falta) y drift (que divergio). Acepta program/project y repo: /kb:audit cheques receivables, /kb:audit drift cheques."
disable-model-invocation: false
---

El usuario quiere comparar la especificacion (discovery) con el codigo implementado. Este skill detecta gaps entre lo documentado y lo construido.

**Tercera fuente — reglas del dominio.** Ademas de discovery vs codigo, comparar contra las `BusinessRule` activas del modulo. Cargar `kb org-context --module {modulo} --format prompt` antes del audit. Si el codigo viola una regla activa, reportarlo como gap categoria `rule-violation` (mayor severidad que un drift normal).

## Parametros

Parsear `$ARGUMENTS`:
- **modo**: `completeness` (default) o `drift`
- **feature**: nombre del program/project (ej: `cheques`)
- **modulo**: modulo del producto (ej: `receivables`)

Ejemplos:
- `/kb:audit cheques receivables` → completeness de cheques en receivables
- `/kb:audit drift cheques receivables` → drift de cheques
- `/kb:audit cheques` → buscar en todos los modulos

## Fase 1 — Leer especificacion

1. Buscar el program/project via CLI:
   - `kb program list` y filtrar por feature/modulo
   - `kb project list --program SLUG` si hay projects

2. Leer contenido relevante via CLI:
   - `kb program show SLUG --full` — metadata + contenido completo (incluye tecnica, negocio, etc.)
   - `kb project show SLUG --full` — metadata + contenido (propuesta, tecnica)
   - `Read ~/.kb-cache/u/{user_id}/programs/{SLUG}/{tipo}.md` o `~/.kb-cache/u/{user_id}/projects/{SLUG}/{tipo}.md` — contenido desde cache local (preferido)
   - `kb content show ID --full-body` — fallback si no esta en cache

3. Extraer checklist de items esperados:
   - **Modelos/Entidades**: tablas, columnas, relaciones del diagrama ER
   - **Endpoints/APIs**: rutas, mutations, queries
   - **Componentes UI**: pantallas, modales, vistas listadas
   - **Flujos**: secuencias de operaciones documentadas
   - **Permisos**: roles y accesos definidos
   - **Validaciones**: reglas de negocio especificadas

## Fase 2 — Explorar codebase

Delegar al agente `codebase-navigator` (Agent tool, subagent_type="codebase-navigator") para buscar cada item del checklist en el codigo:

Prompt al agente:
```
Buscar en el codebase del repo {repo} los siguientes items de la especificacion:

{lista de items con tipo y nombre}

Para cada item, reportar:
- ENCONTRADO: path del archivo, linea aproximada
- NO ENCONTRADO: confirmado que no existe
- PARCIAL: existe pero incompleto (detallar que falta)
```

## Fase 3 — Presentar resultados

### Modo `completeness` — Que falta por implementar

```
AUDIT: {Feature} — Completeness
Spec: {path tecnica.md}
Repo: {repo}

| # | Item | Tipo | Spec | Codigo | Estado |
|---|------|------|------|--------|--------|
| 1 | Cheque (tabla) | Modelo | tecnica.md L45 | src/models/cheque.ts | OK |
| 2 | ChequeDistribution | Modelo | tecnica.md L52 | — | FALTA |
| 3 | POST /cheques | Endpoint | tecnica.md L78 | src/routes/cheques.ts:23 | OK |
| 4 | Modal asignacion | UI | propuesta.md L30 | — | FALTA |
| 5 | Validacion monto | Regla | tecnica.md L90 | src/services/cheque.ts:45 | PARCIAL |

Resumen: 3/5 implementados (60%). 2 faltantes, 0 parciales.

Que quieres hacer?
1. → Ver detalle de items faltantes
2. Crear issues en Linear para items faltantes
3. Parkear
4. Otra cosa
```

### Modo `drift` — Que divergio de la spec

```
AUDIT: {Feature} — Drift
Spec: {path tecnica.md}
Repo: {repo}

| # | Item | Spec dice | Codigo hace | Drift |
|---|------|-----------|-------------|-------|
| 1 | Cheque.status | enum: borrador, activo, cobrado, protestado | enum: draft, active, collected, protested, cancelled | +cancelled no en spec |
| 2 | Distribucion | monto distribuido a facturas | tambien distribuye a anticipos | ampliado vs spec |
| 3 | Permiso protesto | solo admin | cualquier usuario con rol cheques | relajado vs spec |

Resumen: 3 drifts detectados (1 ampliacion, 1 adicion, 1 cambio permisos).

Que quieres hacer?
1. → Actualizar spec para reflejar codigo (propagar al discovery)
2. Reportar drifts como issues
3. Parkear
4. Otra cosa
```

## Fase 4 — Acciones post-audit

Si el usuario elige actualizar la spec:
- Delegar a `doc-writer` (Agent tool, subagent_type="doc-writer") con DOC_ID, TAB_ID, e INSTRUCCION especificando que secciones actualizar. doc-writer maneja tanto contenido de program como de project via Modo C (patch).
- El writer actualiza tecnica y/o propuesta

Si el usuario elige crear issues:
1. Delegar a `issue-writer` (Agent tool, subagent_type="issue-writer") con la lista de items faltantes/divergentes para crear tickets en KB
2. Para cada ticket creado, sincronizar al project tracker via su CLI (resolver operacion `create-issue` desde `tools/*/provider.md`):
   ```bash
   # Resolver comando concreto desde el provider definition del project-tracker
   # Ejemplo: {CLI} issue create --team {team} --title "{titulo}" --description "{desc}" --status Backlog
   kb issue link-external {KB_ID} --external-source {provider_name} --external-id {TRACKER_ID} --external-url {url}
   ```

## Notas

- Este skill es READ-ONLY sobre GitHub y la KB. Solo escribe si el usuario aprueba acciones.
- Para repos que no estan clonados localmente, el codebase-navigator usa la API de GitHub.
- El audit se basa en nombres de entidades, no en comparacion de codigo linea a linea.
- Items "PARCIAL" requieren juicio humano — el skill presenta evidencia, no decide.
