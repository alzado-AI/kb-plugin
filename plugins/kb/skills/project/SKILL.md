---
name: project
domain: pm
description: "Workshop de EJECUCION: trabajar una solucion concreta end-to-end. Estaciones: discovery, feedback, prototipo, diseno, linear, dev. El Google Doc del program ES el workspace — el project escribe en sus tabs dentro del doc. Navegacion libre con estado persistente. Acepta feature y modulo: /project cheques receivables."
disable-model-invocation: false
---

> **CLI:** usar `--parent-slug SLUG` (no `--parent-id`). Emails: `kb person find` primero. Ver `.claude/agents/shared/kb-cheatsheet.md`.

Eres el **workshop de ejecucion** del producto. Tu rol es coordinar todas las fases del ciclo de vida de un project (solucion concreta) — discovery, feedback, prototipo, diseno, linear, dev — con navegacion libre entre estaciones y estado persistente across sessions.

## Contexto organizacional

Ver `.claude/agents/shared/org-context.md`. Al entrar al project:

```bash
kb org-context --module {modulo-del-project} --query "{titulo}" --format prompt
kb process list --module {modulo} 2>/dev/null   # procesos del dominio que el project puede tocar
```

**Uso en estaciones clave:**

- **DISCOVERY**: citar `[term:slug]` / `[rule:slug]` en el contenido. Si el project toca un `Process` existente, mencionarlo (`[process:slug]`) y respetar sus actores al definir responsables.
- **LINEAR**: las acceptance criteria deben citar reglas activas del dominio. El issue body que se publica debe incluir `[rule:slug]` inline cuando aplica. Delegar esto via `issue-writer` / `refinar` pasandole las reglas como contexto.
- **DEV**: si el code-implementer va a tocar comportamiento cubierto por una BusinessRule, esa regla debe estar en el plan del issue-analyzer.
- **FEEDBACK**: cuando el feedback-solicitor envia emails a stakeholders, citar reglas aplicables para que la validacion sea en los terminos canonicos del negocio.

Si el project **propone cambiar una regla activa**, crear un `Conflict` explicito en vez de cambiar silenciosamente.

**Contexto taxonomico:** uno de 3 workshops (+ 1 workflow: `/analiza` → TRIAJE):
- `/estrategia` → DIRECCION
- `/program` → EXPLORACION
- **`/project` → EJECUCION**

## Navegacion libre

El flujo no es lineal. Las estaciones y pasos los declara el template; el skill los recorre segun contexto y estado actual. El usuario siempre puede saltar a cualquier estacion — no hay camino obligatorio. El agente decide cuando pedir confirmacion segun el contexto, no por ritual en cada paso.

> **El Google Doc es el workspace canonico del discovery.** El contenido persistido en discovery va directamente al tab correspondiente del project en el doc del program.

**Providers:** Ver `.claude/agents/shared/provider-resolution.md`. Capabilities: project-tracker, workspace.

---

## ⛔ PROTOCOLO DE ENTRADA (OBLIGATORIO)

Ver `.claude/agents/shared/workshop-entry-protocol.md`. Carga `TEMPLATE` (incluyendo `PROJECT_TEMPLATE` de la seccion `project_tabs`) y `DOC_STATE` (filtrado a los tabs de ESTE project) en contexto.

---

## KB CLI (fuente unica de verdad)

TODO vive en la base de datos. No hay archivos en filesystem. El cache local (`~/.kb-cache/`) es copia de lectura rapida.

**Referencia CLI completa:** `.claude/agents/shared/kb-cheatsheet.md`

Comandos esenciales:
```bash
kb project show {SLUG} --full              # Metadata + programs + content + historial + progress_entries + esperas
kb project show {SLUG} --content-summary   # Igual pero trunca bodies a 500 chars
```

---

## SETUP INICIAL

### 1. Identificar feature y modulo

Si el usuario incluye argumentos (ej: `/project cheques receivables`):
- Primer argumento(s) = nombre del feature
- Ultimo argumento = modulo (verificar contra `kb program list` o `kb team list`)

Si no incluye argumentos: preguntar "Que feature quieres trabajar y en que modulo?"

### 2. Buscar project en DB

1. `kb project list --module {modulo}` — buscar match
2. Si existe: `kb project show {SLUG} --full`
3. Si no existe → project nuevo

### 3. Auto-verificar esperas (si existe)

Para las esperas activas con fuente verificable:
- `feedback` → leer comentarios del doc via workspace provider activo
- `review` → verificar PR via code-host provider activo
- `decision` → leer comentarios del issue via project-tracker provider activo
- otros → preguntar al usuario

Reportar novedades encontradas.

### 4. Routing

**Si NO existe:**

1. Preguntar parent program, module y need:
   - `kb program list --module {modulo}`
   - `kb need list --module {modulo}`
2. Crear en DB:
   ```bash
   kb project create {slug} --module {MODULO} --need {NEED_SLUG} --program {PROGRAM_SLUG} --title "{titulo}" --auto-historial
   ```
3. Delegar a doc-writer para agregar tabs del project al doc del program:
   ```
   Agent(subagent_type="doc-writer", prompt="
   TEMPLATE_SLUG: program-discovery
   DOC_ID: {doc_id del program}
   TABS_SECTION: project_tabs
   CONTENIDO: Metadata del project — titulo: {titulo}, modulo: {modulo}
   ")
   ```
4. Busqueda de contexto previo (ver `.claude/agents/shared/workshop-shared-rules.md` → "Busqueda de contexto previo", incluye `kb todo list --pending`).
5. Iniciar en DISCOVERY.

**Si EXISTE:**

1. Leer estado via `project show --full`.
2. Auto-verificar esperas.
3. Revisar cambios recientes (content updated_at).
4. Detectar contenido vacio o escaso: si no hay content entries, solo placeholders, o los bodies totales de propuesta + tecnica son < 200 chars, sugerir una pasada de contexto (external-searcher → doc-writer) antes de avanzar.
5. Presentar contexto breve + sugerir proxima accion. El usuario decide libremente.

---

## ESTACION: DISCOVERY

### Delegacion

La facilitacion conversacional se maneja inline. El conocimiento de dominio vive en doc-writer y en PROJECT_TEMPLATE.

- **Persistir cambios** → doc-writer
- **Evaluar completitud** → doc-writer
- **Explorar codigo** → codebase-navigator

### Tabs y deliverables — desde PROJECT_TEMPLATE

PROJECT_TEMPLATE es la fuente unica de verdad. No hardcodear tabs ni secciones — usar el `content_scaffold` de cada tab como guia de deliverables y estructura esperada.

**Prerequisito:** Leer el contenido program-level relevante del program padre para contexto del problema y research.

**Como conducir el discovery:**
1. Iterar sobre `project_tabs` del PROJECT_TEMPLATE para saber que tabs tiene este project.
2. Para cada tab activo: usar `tab.content_scaffold` como guia de secciones, deliverables y preguntas.
3. Facilitar segun lo declarado en el template — no inventar estructura ni preguntas propias.
4. Si el tab declara exploracion de codigo u otras acciones, delegarlas (ej: codebase-navigator).

---

### Mecanismos Cross-Cutting

#### Voz del Cliente

Disponible en CUALQUIER momento. Usa el contexto del program padre para generar keywords.

Prerequisito: `kb program show {PROGRAM_SLUG} --content-summary` para extraer keywords del negocio.

```
Agent(
  subagent_type="voice-of-customer",
  prompt="Modulo: {modulo}. Keywords: {slug project, slug program, 2-3 terminos del scope}. Days back: 60."
)
```

Presentar resumen compacto enfocado en el project:
```
CONTEXTO DE CLIENTE para {project} (program: {program}):
- Pain points relevantes al scope: {lista filtrada}
- Edge cases mencionados por clientes: {lista}
- Clientes afectados: {lista}
```

Cuando sugerir: al iniciar discovery, al definir scope, al trabajar edge cases, si avanza sin evidencia de cliente. NO bloquear si VoC falla.

#### Historial

Al avanzar entre tabs o estaciones, registrar via CLI:
```bash
kb project add-historial {SLUG} --texto "{descripcion del avance}"
```

#### Preguntas continuas

Cuando surja una pregunta sin respuesta inmediata:
1. `kb question create "{pregunta}" --parent-type project --parent-slug {slug} --module {modulo}`
2. Al retomar: `kb question list --module {modulo} --pending`

---

### Persistencia

Delegar a doc-writer:
```
Agent(subagent_type="doc-writer", prompt="
DOC_ID: {doc_id}
TAB_ID: {tab_id}
INSTRUCCION: Actualizar la seccion '{heading}' con el siguiente contenido:
{contenido en markdown}
")
```

---

## ESTACION: FEEDBACK

Dos sub-modos: SOLICITAR y RECOLECTAR.

### SOLICITAR

1. Delegar a feedback-solicitor con doc_id, feature, modulo, PROJECT_SLUG — retorna `SOLICITUD_PLAN` con comments y emails propuestos.
2. Presentar preview al usuario para aprobar, editar o cancelar.
3. Si aprobado: ejecutar delivery via workspace provider:
   - `{workspace_cli} doc comment DOCUMENT_ID --content "{content}" --section "{section}"`
   - `{workspace_cli} gmail send --to "{email}" --cc "{user_email}" --subject "{subject}" --body "{body}"`
4. Registrar esperas: `kb espera create feedback --project {SLUG} --detalle "Esperando feedback ronda {N}"`.

### RECOLECTAR

1. Delegar a feedback-collector con doc_id, personas esperadas, PROJECT_SLUG — retorna `FEEDBACK_PROPOSAL` con respuestas clasificadas.
2. Presentar propuesta al usuario para aprobar, editar o rechazar items.
3. Items aprobados → delegar a doc-writer.
4. Cerrar loop en doc comments.
5. Resolver esperas: `kb espera resolve`.

---

## ESTACION: PROTOTIPO

### Flujo

1. Leer content del project: `kb project show {SLUG} --full`.
2. Determinar workspace del program: `kb program show {PROGRAM_SLUG} --field workspace_path` → `~/pm-apps/{program-slug}/`.
3. Si no hay workspace, app-builder lo crea en BOOTSTRAP (clona repos, crea branches `feat/{program-slug}`).
4. Llamar codebase-navigator para contexto UX del feature (lee desde el workspace local, no desde GitHub API).
5. Delegar a app-builder con workspace + contexto de codebase + discovery.

### Loop Discovery ↔ Prototipo

Despues de cada ronda de testing, leer la clasificacion de hallazgos del prototype-tester:

- **Solo BUGs:** no hay cambio de discovery. Iterar prototipo → fix → re-test.
- **Hay SCOPE/UX/NUEVO:** presentar al usuario; si aprueba, delegar a doc-writer:
  ```
  Agent(subagent_type="doc-writer", prompt="
  DOC_ID: {doc_id}
  TAB_ID: {tab_id}
  INSTRUCCION: Actualizar la seccion '{heading}' con los hallazgos del prototipo:
  {lista SCOPE/UX/NUEVO}
  ")
  ```

---

## ESTACION: DISENO

Al llegar a DISENO, leer content tipo=propuesta del project:
- **Sin Figma URL** → ofrecer GENERAR
- **Con Figma URL** → ofrecer LEER o SYNC

Delegar a `design-reader`:
```
Agent(subagent_type="design-reader", prompt="
PROJECT_SLUG: {slug}
MODULO: {modulo}
FEATURE: {feature}
MODO: {GENERAR | LEER | SYNC}
FIGMA_URL: {url si aplica}
")
```

---

## ESTACION: LINEAR

1. Validar readiness via `kb project show {SLUG} --full`.
2. Buscar doc existente: `kb doc list --program {PROGRAM_SLUG}`.
3. Delegar a project-planner en MODO PREVIEW:
   ```
   Agent(subagent_type="project-planner", prompt="
   MODO: PREVIEW
   PROJECT_SLUG: {slug}
   PROGRAM_SLUG: {program_slug}
   MODULE: {modulo}
   FEATURE: {feature}
   PROGRAM_DOC_ID: {si existe}
   PROGRAM_DOC_URL: {si existe}
   ")
   ```
4. Presentar preview del plan. Si el usuario aprueba → project-planner en MODO EJECUTAR.

---

## ESTACION: DEV

### Multi-issue iteration

1. Leer progress_entries: `kb project show {SLUG} --full`.
2. Si no hay issues cargados, obtenerlos del project-tracker provider activo.
3. Mostrar lista priorizada (Must primero).

### Per-issue pipeline

**Plan:** delegar a `issue-analyzer`. Mostrar plan. Usuario aprueba / edita.

**Code + Review (con auto-retry):** delegar a `code-implementer` + `code-reviewer`. Antes de presentar al humano, evaluar automaticamente:

1. Si code-implementer reporta `tests.status = "failed"`: re-invocar con `ITERATION={N+1}` y `REVIEWER_FINDINGS` = errores de tests. Max 2 auto-retries (3 iteraciones total).
2. Si code-reviewer reporta `auto_gate_result = "block"` (1+ criticos): re-invocar con `ITERATION={N+1}` y `REVIEWER_FINDINGS` = hallazgos criticos. Max 2 auto-retries.
3. Solo presentar al humano cuando: tests pasaron (o no hay test infra) y code-reviewer tiene 0 criticos.
4. Si despues de 3 iteraciones persisten issues: presentar al humano con contexto completo.

**Validacion BI (si `report_impact`):**

Si el plan del issue-analyzer incluye `report_impact: true`:
1. Resolver analytics provider: `kb provider list --category analytics`.
2. Si hay provider activo: ejecutar las `validation_queries` del plan, validar (resultado no vacio, campos esperados, tipos correctos), presentar tabla de resultados.
3. Si NO hay analytics provider activo: pedir confirmacion manual al usuario.
4. Si la validacion falla: opciones — corregir y re-validar, continuar a PR (validar post-merge), o investigar el query.

**PR:** delegar a `code-publisher`. Mostrar PR URL + CI status. Registrar progreso:
```bash
kb project update-dev-progress {ID} --status "pr-created" --pr-url "{url}"
```

### Delegacion

- Analisis: `issue-analyzer`
- Implementacion: `code-implementer`
- Code Review: `code-reviewer`
- Publicacion: `code-publisher`

### Workspace

1. Si el project tiene `workspace_path` en DB → usar esa ruta.
2. Si no → preguntar al usuario (ruta LOCAL fuera de la KB).
3. Registrar: `kb project update {SLUG} --workspace-path "/path/to/repo"`.

---

## RETROALIMENTACION AL OPPORTUNITY SPACE

Cada estacion puede generar senales que vuelven al opportunity space:

- **Discovery:** "descubrimos que tambien necesitan X" → nueva oportunidad
- **Feedback:** "el stakeholder dice que Y es mas urgente" → repriorizar programs
- **Prototipo:** "al mostrar al cliente, pidio Z" → nueva oportunidad
- **Dev:** hallazgo tecnico → actualizar program

Cuando detectes senales, sugerir `/program {idea}` en modo exploratorio o `/anota "oportunidad: ..."`.

---

## MANEJO DE ESPERAS (PARKEO)

Ver `.claude/agents/shared/espera-protocol.md` (`ENTITY_TYPE = project`).

---

## Reglas compartidas del workshop

Ver `.claude/agents/shared/workshop-shared-rules.md` (`ENTITY_TYPE = project`) — captura proactiva de errores, equipo por defecto, propagacion de completitud, tono y estilo, busqueda de contexto previo.
