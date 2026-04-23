# KB CLI — Referencia rapida para agentes

Leer ANTES de ejecutar cualquier comando KB. Evita errores comunes. Uso: `kb <entity> --help` para flags completos.

## Entidades y comandos

| Entidad | Comandos | Notas |
|---------|----------|-------|
| **module** | list, show, create | create: `SLUG [--name N] [--owner-pm EMAIL] [--em EMAIL]`. Slugs en ingles |
| **objective** | list, show, create, update, delete | `--semester S` en list/create |
| **need** | list, show, create, update, delete | Customer JTBD. create: `SLUG --module M [--title T] [--description D] [--position N]`. show: `--signals`. list: `--module M` con signal counts |
| **program** | list, show, create, update, delete, set-content, link-need, unlink-need, link-objective, unlink-objective, link-project, link-person, link-program, add-readiness, complete-readiness, add-historial | show: `--full`, `--content-summary`, `--field F`. update: `--estado`, `--rice "R:5 I:2 C:70% E:3"`, `--estacion`, `--bloqueado`, `--new-slug S` (rename transaccional: migra workspace_path/folder_path + paths de todos sus projects). delete: solo si sin projects/contenido. set-content: `--tipo T --file F` o `--curated-file F` |
| **project** | list, show, create, update, add-readiness, complete-readiness, add-historial, link-person, add-progress-entry, update-progress-entry | show: `--full`, `--content-summary`, `--field F`. create: `[--program T] [--module M] [--need J] [--auto-historial]`. update: `--estado`, `--checkpoint`, `--module M`, `--need J`, `--estacion`, `--escala`, `--workspace-path`, `--new-slug S` (rename transaccional: migra workspace_path/folder_path). list: `--module M`, `--program T`, `--estado E` |
| **person** | list, find, show, create, update | create: `NAME EMAIL --rol R [--upsert] [--force] [--company C]`. find: busca por nombre |
| **todo** | list, find, create, complete, delete, add-stakeholder, remove-stakeholder | Universal to-do. `--parent-type T --parent-id N` o `--parent-slug S`. Roles: solicitante, destinatario, reportero, interesado. delete: hard-delete permanente (preferir `complete` para audit trail); soporta bulk con `--parent-type T --parent-id N`/`--parent-slug S` sin ID. `kb action` alias hidden. |
| **meeting** | list, show, create, add-attendee, add-decision, search | create: `TITLE --fecha DATE [--canal C] [--module M]`. add-decision: `--need SLUG` |
| **question** | list, show, create, answer | `--parent-type T --parent-id N` o `--parent-slug S`. `--pending` en list |
| **doc** | list, find, register, show, upload, share, unshare, delete | Documents y files unificados (`source: external\|internal`). list: `--source`, `--parent-type`, `--parent-id`, `--module`, `--tipo`, `--program`. register: `NAME LINK --tipo T` (externo). upload: `PATH [--parent-type T --parent-id ID]` (interno, auto-share 7d). Parent opcional: con sesion activa se auto-linkea; sin parent ni sesion el doc se sube como orphan (warn en stderr). `--no-session` para silenciar warn en uploads headless. share/unshare: token publico. |
| **report** | list, show, create, update, delete, generate, variants, variant-show, variant-delete, preflight | Pipeline-backed file artifacts. create: `SLUG --name N --pipeline P [--param NAME:TYPE[:LABEL]] [--output-format xlsx\|pdf\|csv\|html\|json] [--module M] [--visibility V]`. generate: `SLUG [--params JSON] [--timeout N] [--no-wait] [--force]` — responde **202 Accepted** (kickoff async); el CLI hace polling hasta `completed`/`failed` o hasta agotar `--timeout` (default 300s). `--no-wait`: retorna tras el 202 sin polling. `--force`: si hay variant activa con mismos params, la borra y regenera. Variant pasa `running` → `completed`/`failed`. Duplicate activo sin `--force` → 409 con `existing_variant`. preflight: `SLUG [--params JSON]` (valida params sin correr). variants: `SLUG [--filter params.KEY=VAL] [--status S]`. Alias deprecated: `kb view` (shim, se elimina en release futuro). |
| **learning** | list, show, create, search | create: `TITLE --tipo T [--body B] [--source S] [--sources URL1,URL2,...]`. `--sources`: lista de URLs consultadas (trazabilidad multi-fuente). |
| **team** | list, show, create, add-member | create: `NAME [--tipo T] [--module M] [--em EMAIL]` |
| **context** | list, show, set | `KEY VALUE [--section S]` |
| **company** | list, show, create, update | create: `NAME --tipo T [--segment S] [--industry I] [--lifecycle L] [--owner EMAIL] [--annual-revenue N]`. list: `--tipo T`, `--segment S`, `--lifecycle L`. Campos: segment (enterprise/mid-market/smb/startup), lifecycle_stage (lead/prospect/onboarding/active/expansion/at-risk/churned), external_id/external_source para sync CRM |
| **opportunity** | list, show, create, update, history | create: `SLUG --stage S [--company C] [--owner EMAIL] [--revenue N] [--probability P] [--currency CUR]`. update: `--stage S`, `--lost-reason R`, `--closed-at D`, `--currency CUR`. list: `--stage S`, `--company C`. history: `SLUG` (lee EstadoHistorial). Stages: prospecting, qualifying, proposal, negotiation, closed-won, closed-lost |
| **account-plan** | list, show, create, update, link, unlink | create: `SLUG [--company C] [--periodo P] [--owner EMAIL] [--strategy S]`. link: `SLUG --opportunity OPP_SLUG [--priority P]`. unlink: `SLUG --opportunity OPP_SLUG`. list: `--company C` |
| **sales-goal** | list, show, create, update, link, unlink | create: `NAME --periodo P [--metric M] [--target T] [--owner EMAIL]`. update: `ID --actual V`. link: `ID --opportunity SLUG [--contribution N]`. unlink: `ID --opportunity SLUG`. list: `--periodo P`, `--module M` |
| **contract** | list, show, create, update | create: `SLUG --title T [--company C] [--tipo T] [--amount N] [--billing-frequency F] [--start-date D] [--end-date D]`. update: `SLUG --estado E [--cancel-reason R]`. list: `--company C`, `--estado E`, `--por-renovar`. Estados: borrador, negociacion, activo, por-renovar, renovado, cancelado, vencido |
| **invoice** | list, show, create, update | create: `NUMBER --amount N --issue-date D [--company C] [--due-date D] [--currency CUR]`. update: `NUMBER --estado E [--paid-date D] [--paid-amount N]`. list: `--company C`, `--estado E`, `--overdue`. Estados: borrador, emitida, enviada, parcial, pagada, vencida, anulada |
| **interaction** | list, show, create | create: `--company C --tipo T --summary S --direction D --occurred-at DT [--channel CH]`. list: `--company C`, `--tipo T`, `--since DATE`. Tipos: email, call, meeting, demo, support, other. Direction: inbound, outbound |
| **product** | list, show, create, update | create: `SLUG --name N [--category C] [--unit-price P] [--currency CUR]`. list: `--category C` |
| **line-item** | add, list, remove | add: `--parent-type T --parent-id ID --unit-price P [--product SLUG] [--quantity Q]`. list: `--parent-type T --parent-id ID`. Parent types: opportunity, contract, invoice |
| **cashflow** | list, show, create | create: `TIPO AMOUNT FECHA [--company C] [--opportunity O] [--invoice I] [--due-date D] [--description D]`. list: `--company C`, `--overdue`, `--tipo T`. Campos nuevos: company, opportunity, invoice, due_date, external_id |
| **budget** | list, show, create, update | create: `SLUG --name N --periodo P [--module M] [--amount-planned N]`. update: `SLUG --amount-executed N` |
| **compliance** | list, show, create, update, complete | `--overdue` en list |
| **gate** | list, create, approve, reject | `--parent-type T --parent-id N` o `--parent-slug S`. Cualquier domain pack. |
| **espera** | list, create, resolve | `--parent-type T --parent-id N` o `--parent-slug S`. `--active` en list. |
| **issue** | list, show, create, update, resolve, cancel, delete, find, link-external | create: `TITLE --tipo T --priority P --module M [--need SLUG]`. list: `--need SLUG`. cancel: soft-delete (estado=cancelado, conserva historial). delete: hard-delete permanente |
| **conversation** | list, show, create, update, add-ref, search, trace | thread tracking |
| **content** | show, push | show: `--full-body`. push: `--body B` o `--file F`. Usa `parent_type/parent_id` generico. |
| **domain** | list, show, entities, seed | `entities` lista registry. `seed` inicializa core. Domain packs se activan por separado. |
| **template** | list, show, create, update, search, delete, pull | create: `SLUG --name N --tipo T [--body B] [--file F]`. Cache: `~/.kb-cache/u/{user_id}/templates/{slug}.md`. Tipos: issue, spec, replicacion, agente, script, crm-import, erp-report, sales-advisor |
| **access** | show, grant, revoke, set-visibility | grant: `--user EMAIL | --group SLUG --level read|comment|write [--propagate]`. set-visibility: `--visibility org|restricted|private [--org-level read|comment|write]` |
| **feedback** | list, show, create, update, find, triage, plan, respond, derive, resolve | create: `TITLE --raw-message MSG [--client-name N] [--client-email E] [--client-company C]`. triage: `ID --triage-summary S --clasificacion C --severidad S [--module M] [--duplicates JSON]`. plan: `ID --execution-plan PLAN`. respond: `ID --client-response RESPUESTA` (clasif=recomendacion, crea notificacion). resolve: `ID [--note NOTE]`. list: `[--estado E] [--clasificacion C] [--pretty]`. find: `KEYWORDS`. |
| **notification** | list, show, mark-read, mark-all-read, count | list: `[--unread] [--pretty]`. show: `ID`. mark-read: `ID`. count: devuelve total no leidas. |
| **comment** | add, list, delete | add: `ENTITY_TYPE SLUG_OR_ID --body TEXT`. delete: `COMMENT_ID` |
| **dashboard** | list, show, create, update, delete, add-card, remove-card, reorder, render, export | create: `SLUG --name N [--module M] [--parameters JSON] [--layout JSON]`. add-card: `DASH_SLUG CARD_SLUG [--position '{"x":0,"y":0,"w":4,"h":3}'] [--param-overrides '{"card_param":"dash_param"}']`. render: `SLUG [--params JSON]` (ejecuta todas las cards). export: `SLUG --output F --format json`. |
| **card** | list, show, create, update, delete, execute, result, runs, export | data_source.type **solo `workflow`** (Phase 2). create: `SLUG --data-source '{"type":"workflow","config":{"pipeline_slug":"kb-query","input":{"entity":"todo","args":"--pending"}}}' --viz-type TYPE [--name N] [--module M] [--parameters JSON] [--default-params JSON] [--viz-config JSON] [--cache-ttl N]`. execute: `SLUG [--params JSON] [--force]` (bloquea hasta que el Pipeline termina). Para queries a KB usar Pipeline canonico `kb-query`; para CLIs externos crear Pipeline con step `code`. Pipelines de Cards solo pueden tener step types deterministas (code/router/foreach), nunca agent/approval. |

## Output

- **JSON por default**, **`--pretty`** agrega Rich tables
- `show --full`: metadata + relations + content (body completo) + gates + readiness + historial + esperas
- `--content-summary`: igual que `--full` pero trunca bodies a 500 chars
- `--field`: extrae campo por dot-notation (ej: `--field content.negocio.id`)
- `search` retorna `body_preview` (200 chars) y cubre: program, project, objective, content, learning, meeting, todo, question, decision, issue, conversation, report

### JSON vs --pretty (multi-usuario)

`--pretty` usa columnas hardcodeadas que **ocultan** `visibility`, `org_level`, `created_by`. Si necesitas saber quien creo un item o si puedes editarlo, usar JSON (sin `--pretty`).

| Modo | Campos visibilidad | Usar para |
|------|-------------------|-----------|
| `kb program list` (JSON) | `created_by`, `visibility`, `org_level` | Analisis, filtrado, diagnosticos |
| `kb program list --pretty` | Ocultos | Mostrar al usuario |

**Obtener mi UUID:** `kb auth status` → campo `uuid`.

**Clasificacion rapida:**
- `created_by == mi_uuid` → mio, puedo editar
- `visibility == "org"` + `org_level == "write"` → de la org, puedo editar
- `visibility == "org"` + `org_level == "read"` → de la org, solo lectura
- `visibility == "private"` → si lo veo es mio (la API filtra automaticamente)

## Infraestructura y queries

```bash
kb status                              # Conteos y ultima actualizacion
kb search KEYWORD [--type program,meeting] [--limit N] [--pretty]

# Sync (bidireccional local cache <-> DB)
kb sync                                # Detecta diffs, muestra status, NO aplica cambios
kb sync --apply                        # Aplica cambios no-conflictivos
kb sync --force-push | --force-pull    # Resuelve conflictos
kb sync --pull-only | --push-only      # Unidireccional

# Queries cross-cutting
kb query scanner-summary [--module M]   # Snapshot consolidado (1 call)
kb query coverage PROGRAM_SLUG         # Projects + gaps de un program
kb query cross-programs PROJECT_SLUG   # En que programs aparece un project
kb query gaps                          # Objectives sin programs, programs sin need, etc.
kb query need-evidence NEED_SLUG       # Programs (M2M) + senales + evidence_weight
kb query active-esperas [--module M]   # Esperas sin resolver
kb query pipeline-status [--module M]  # Programs/projects por estacion con blockers

# Lint y heal
kb lint check [--module M] [--program T] [--project M] [--pretty]
kb lint heal [--dry-run] [--pretty]
```

## Gotchas

### 1. Slug vs ID

| Comando | Acepta slug | Acepta ID | `--parent-slug` |
|---------|:-----------:|:---------:|:---------------:|
| `kb program show SLUG` | slug | - | - |
| `kb project show SLUG` | slug | - | - |
| `kb todo create --parent-type T --parent-slug S` | - | `--parent-id` (int) | `--parent-slug` (text) |
| `kb question create --parent-type T --parent-slug S` | - | `--parent-id` (int) | `--parent-slug` (text) |
| `kb espera create --parent-type T --parent-slug S` | - | `--parent-id` (int) | `--parent-slug` (text) |
| `kb todo add-stakeholder TASK_ID EMAIL` | - | int | - |
| `kb meeting add-decision MEETING_ID TEXT` | - | int | - |

**Regla:** Usar `--parent-slug` siempre que tengas el slug. NO usar `--parent-id` con un slug — fallara.

**Parent types soportados por `--parent-slug`:** program, project, need, module, objective, issue, conversation, opportunity, account-plan, budget, template.

### 2. Emails — SIEMPRE buscar antes de usar

**NUNCA adivinar emails.** Siempre resolver antes:

```bash
kb person find "{apellido}"    # Busca por nombre/apellido
# → [{"name": "Ana Pérez", "email": "ana.perez@empresa.com"}]
# LUEGO usar el email exacto:
kb todo add-stakeholder 405 ana.perez@empresa.com --rol destinatario
```

**Aplica a:** `todo add-stakeholder`, `program link-person`, `project link-person`, `meeting add-attendee`, `person update`.

### 3. Decisiones de reunion — tabla decisions, NO texto suelto

Persistir con `meeting add-decision`, NO como parte del `--raw-content` o `--summary`:

```bash
kb meeting add-decision {MEETING_ID} "Decision texto" --module receivables --program cheques [--need cobrar]
```

**Flags opcionales de trazabilidad:** `--module M`, `--program T`, `--project M`, `--need J`.

### 4. Patron: resolver ID numerico

Para comandos que solo aceptan ID: obtener del JSON de salida del `create` o `show`.

### 5. Errores comunes

| Error | Causa | Fix |
|-------|-------|-----|
| `'cheques' is not a valid integer` | Slug en `--parent-id` | Usar `--parent-slug cheques` |
| `Person with email 'aperez@empresa.com' not found` | Email adivinado | `kb person find "fernandez"` primero |
| Decisiones no aparecen en queries | Texto, no `add-decision` | Usar `kb meeting add-decision` |
| `--parent-slug not supported for parent_type 'X'` | parent_type sin slug | Usar `--parent-id` con ID numerico |

### 6. Contexto del usuario y providers

Cuando el usuario pregunte sobre su identidad, cuentas, o configuracion — buscar en KB/providers ANTES de ir a memoria o preguntar.

Cadena de descubrimiento:
1. `kb auth status` → email, role, uuid del usuario actual
2. `kb person show EMAIL` → perfil completo, company, teams, modules
3. `kb credential list` → providers configurados con env_var_name
4. `kb provider list --check` → providers activos con status
5. Provider CLI → consultar la operacion relevante del provider. Resolver CLI y comando desde `kb provider list` → leer su `definition_path` (provider.md)

| Entidad | Comandos | Notas |
|---------|----------|-------|
| **auth** | status, login, logout | status: identidad del usuario actual |
| **credential** | list, set, delete | Per-user. list: solo metadata (provider, alias, credential_type, env_var_name) — valores nunca expuestos al CLI |
| **provider** | list | `--check` valida conectividad. `--category C` filtra |

### Investigar providers — no confundir estatico con runtime

Cuando investigues si un provider esta registrado o si una operacion existe, la lectura estatica del codigo NO es suficiente. El modulo puede contener `@register(...)` y aun asi caerse del REGISTRY si el import chain falla (ocurrio con google pre-fix: import de `RunArtifact` en `apps.workflow` rompia silenciosamente via `except ImportError: pass`). Siempre verificar runtime:

1. `kb provider list --check` — estado reportado por el backend live
2. `curl $KB_API_URL/api/v1/providers/catalog/` — lista exacta de ops que el CLI consume
3. `pytest backend/apps/providers/tests/test_catalog_coverage.py` — guard estructural

Nunca reportar "provider X tiene N ops registradas" basado solo en ver decoradores — eso describe lo que el codigo INTENTA hacer, no lo que el backend HACE.
