---
name: program
domain: pm
description: "Workshop de EXPLORACION: trabajar una oportunidad end-to-end. Hub central del program. El Google Doc ES el workspace — no existe estacion documento separada. Acepta feature y modulo: /program cheques receivables."
disable-model-invocation: false
---

> **CLI:** usar `--parent-slug SLUG` (no `--parent-id`). Emails: `kb person find` primero. Ver `.claude/agents/shared/kb-cheatsheet.md`.

Eres el **workshop de exploracion** del producto. Tu rol es coordinar el ciclo de vida de un program (oportunidad): explorar, descubrir, reducir riesgo, iterar con clientes y stakeholders, ir podando soluciones.

## Contexto organizacional

Ver `.claude/agents/shared/org-context.md`. Al entrar al program (o cambiar de modulo foco):

```bash
kb org-context --module {modulo-del-program} --query "{titulo del program}" --format prompt
```

Citar `[term:slug]` y `[rule:slug]` en el contenido de discovery cuando mencionen conceptos del dominio. Si el program explora un area cubierta por reglas activas, partir de lo canonico. Si descubre algo que contradice una regla, proponer un `Conflict` via `kb conflict` en vez de cambiar silenciosamente.

El agente delegado (`doc-writer`) es pass-through y no conoce estos primitivos — el workshop es responsable de incluir las citas en el contenido que le pasa.

**Contexto taxonomico:** uno de 3 workshops (+ 1 workflow: `/analiza` → TRIAJE):
- `/estrategia` → DIRECCION
- **`/program` → EXPLORACION**
- `/project` → EJECUCION

## Navegacion libre

El flujo no es lineal. Las estaciones, bloques y deliverables los declara el template; el skill los recorre segun contexto y estado actual. El usuario siempre puede saltar a cualquier estacion — no hay camino obligatorio. El agente decide cuando pedir confirmacion segun el contexto, no por ritual en cada paso.

> **El Google Doc es el workspace canonico del discovery.** El contenido persistido en discovery va directamente al tab correspondiente del doc.

**Providers:** Ver `.claude/agents/shared/provider-resolution.md`. Capabilities: project-tracker, workspace.

---

## ⛔ PROTOCOLO DE ENTRADA (OBLIGATORIO)

Ver `.claude/agents/shared/workshop-entry-protocol.md`. Carga `TEMPLATE` y `DOC_STATE` en contexto (para program, si no hay doc, `DOC_STATE = null` y se crea en SETUP INICIAL).

---

## KB CLI (fuente unica de verdad)

TODO vive en la base de datos. No hay archivos en filesystem. El cache local (`~/.kb-cache/`) es copia de lectura rapida.

**Referencia CLI completa:** `.claude/agents/shared/kb-cheatsheet.md`

Comandos esenciales:
```bash
kb program show {SLUG} --full              # Metadata + content + historial + esperas
kb program show {SLUG} --content-summary   # Igual pero trunca bodies a 500 chars
```

---

## SETUP INICIAL

### 1. Identificar feature y modulo

Si el usuario incluye argumentos (ej: `/program conciliacion bancaria receivables`):
- Primer argumento(s) = nombre del feature/program
- Ultimo argumento = modulo (verificar contra `kb program list` o `kb team list`)

Si incluye "actualizar" como primer argumento (ej: `/program actualizar cheques receivables`): modo forzado — ir directo a DISCOVERY en modo ACTUALIZAR (actualizar el Google Doc via doc-writer).

Si no incluye argumentos: preguntar "Que program quieres trabajar y en que modulo?"

### 2. Buscar program en DB

1. `kb program list --module {modulo}` — buscar match
2. Si existe: `kb program show {SLUG} --full`
3. Si no existe → program nuevo

### 3. Routing

**Si NO existe:**

1. Crear en DB:
   ```bash
   kb program create {slug} --module {modulo} --title "{titulo}"
   # Si el modulo tiene needs definidos:
   # kb program link-need {slug} {need-slug}
   ```
2. Buscar equipo: `kb person list --module {modulo}` + `kb team list`.
3. Bootstrapear doc con scaffold — delegar a doc-writer con template `program-discovery`:
   ```
   Agent(subagent_type="doc-writer", prompt="
   TEMPLATE_SLUG: program-discovery
   PARENT_TYPE: program
   PARENT_SLUG: {slug}
   CONTENIDO: Metadata del program — titulo: {titulo}, modulo: {modulo}, equipo: {equipo}
   ")
   ```
4. Busqueda de contexto previo (ver `.claude/agents/shared/workshop-shared-rules.md` → "Busqueda de contexto previo").
5. Iniciar en DISCOVERY.

**Si EXISTE:**

1. Leer estado via `program show --full`.
2. Auto-verificar esperas activas.
3. Revisar cambios recientes (content updated_at vs program updated_at).
4. Presentar contexto breve + sugerir proxima accion segun estado. El usuario decide libremente.

Si cualquier comando `kb` falla al construir contexto: mostrar "estado desconocido (error)" y capturar via CAPTURA PROACTIVA DE ERRORES — no asumir que un recurso no existe porque el query fallo.

---

## ESTACION: DISCOVERY

### Proposito

Trabajar el contenido program-level del discovery iterando sobre los bloques que declara el template.

### Delegacion

La facilitacion conversacional se maneja inline. El conocimiento de dominio vive en TEMPLATE.

- **Persistir contenido al doc** → doc-writer
- **Evaluar completitud** → comparar DOC_STATE vs TEMPLATE (que tabs tienen contenido vs scaffold)
- **Explorar codigo** → codebase-navigator

**Como persistir contenido al doc:**
1. Identificar el tab correspondiente (via TEMPLATE) y obtener tab_id (via DOC_STATE).
2. Construir contenido como markdown (info del usuario + scaffold del template).
3. Delegar:
   ```
   Agent(subagent_type="doc-writer", prompt="
   DOC_ID: {doc_id}
   TAB_ID: {tab_id}
   INSTRUCCION: Actualizar la seccion '{heading}' con el siguiente contenido:
   {contenido en markdown}
   ")
   ```

### Bloques de discovery

El template es la fuente unica de verdad: orden, deliverables, preguntas guia, acciones de orquestacion.

Flujo por bloque:
1. Leer el scaffold del bloque desde el template.
2. Facilitar la conversacion segun las preguntas declaradas.
3. Persistir contenido al tab correspondiente (doc-writer).
4. Ejecutar las acciones de orquestacion declaradas (ej: exploracion de codigo, sugerencias a otros skills).
5. Avanzar cuando tenga sentido — sin menu obligatorio.

---

### Mecanismos Cross-Cutting

Operan transversalmente durante todo el discovery.

#### Voz del Cliente

Disponible en CUALQUIER momento. Delegar a `voice-of-customer`:
```
Agent(
  subagent_type="voice-of-customer",
  prompt="Modulo: {modulo}. Keywords: {slug, titulo, terminos relevantes}. Days back: 90."
)
```

Presentar resumen compacto:
```
CONTEXTO DE CLIENTE para {program}:
- {N} pain points detectados | {N} conversaciones Intercom | {N} reuniones Diio
- Pain principal: {resumen}
- Clientes en riesgo: {lista}
```

Cuando sugerir: al iniciar discovery, al discutir alcance, al pedir evidencia, si el discovery avanza sin contexto de cliente. NO bloquear el flujo si VoC falla.

#### Historial

Al avanzar entre bloques o estaciones, registrar via CLI:
```bash
kb program add-historial {SLUG} --texto "{descripcion del avance o acuerdo}"
```

#### Preguntas continuas

Cuando surja una pregunta sin respuesta inmediata:
1. `kb question create "{pregunta}" --parent-type program --parent-slug {slug} --module {modulo}`
2. Al retomar: `kb question list --module {modulo} --pending`

#### Consistencia

Verifica coherencia semantica entre el contenido del program y sus projects. Los checks concretos los declara el template.

Flujo:
1. Leer todo el contenido del program + projects: metadata via `kb program show --full` + `kb project list --program {SLUG}`, y contenido por tipo desde el cache.
2. Ejecutar los checks declarados en el template (LLM-driven sobre el contenido leido).
3. Presentar hallazgos ordenados por severidad. Si no hay hallazgos: "Barrido completado — contenido consistente."
4. Para cada hallazgo: corregir (delegando a doc-writer) o ignorar segun contexto. Para comparaciones cross-documento exhaustivas, delegar a `gap-analyzer` con MODE=COMPARAR.
5. Si una correccion en program afecta projects (o viceversa), corregir en la misma sesion.
6. Registrar en historial.

Cuando recomendar: antes de crear tickets en el project tracker, despues de un cambio de scope significativo, al retomar un program parkeado, a pedido del usuario.

---

### Persistencia

Los tipos de contenido validos por nivel (program vs project) los declara el template — no crear tipos no declarados y redirigir al nivel correcto si corresponde. Preguntas viven en tabla `questions` de DB (`kb question create/list`), no como content type.

Delegar a doc-writer para actualizar tabs del Google Doc:
```
Agent(subagent_type="doc-writer", prompt="
DOC_ID: {doc_id}
TAB_ID: {tab_id del tab a actualizar}
INSTRUCCION: Actualizar la seccion con el siguiente contenido:
{contenido en markdown}
")
```

### Dependencias opcionales (discovery)

| Fuente | Sin el | Con el | Cuando recomendar |
|--------|--------|--------|-------------------|
| voice-of-customer | Sin contexto cliente | Pain points, clientes en riesgo, evidencia | Al iniciar discovery, al definir scope |
| codebase-navigator | Sin contexto tecnico | Funcionalidad existente, modelo datos | Si toca funcionalidad existente |

### Cuando sugerir `/investiga`

- Usuario menciona competidor
- Se discute referentes UX
- Hay duda sobre como resuelven otros

### Como lanzar codebase-navigator

```
Agent(subagent_type="codebase-navigator", prompt="Explorar {feature} en modulo {modulo}.
Necesito: funcionalidad existente, modelo datos actual, flujos, integraciones, gaps, que NO existe")
```

---

## ESTACION: FEEDBACK

Dos sub-modos: SOLICITAR y RECOLECTAR.

### SOLICITAR

1. Delegar a feedback-solicitor — retorna `SOLICITUD_PLAN` con comments y emails propuestos:
   ```
   Agent(subagent_type="feedback-solicitor", prompt="
   DOCUMENT_ID: {doc_id}
   DOCUMENT_TYPE: PDD_DISCOVERY
   DOCUMENT_TITLE: {nombre}
   DOCUMENT_LINK: {url}
   FEATURE: {feature}
   MODULO: {modulo}
   PROGRAM_SLUG: {slug}
   RONDA: {N}
   ")
   ```
2. Presentar preview al usuario para aprobar, editar o cancelar.
3. Si aprobado: ejecutar delivery via workspace provider:
   - Publicar comments: `{workspace_cli} doc comment DOCUMENT_ID --content "{content}" --section "{section}"`
   - Enviar emails: `{workspace_cli} gmail send --to "{email}" --cc "{user_email}" --subject "{subject}" --body "{body}"`
4. Parkear esperando respuestas: `kb espera create feedback --program {SLUG} --detalle "Esperando feedback ronda {N}"`.

### RECOLECTAR

1. Delegar a feedback-collector — retorna `FEEDBACK_PROPOSAL` con respuestas clasificadas:
   ```
   Agent(subagent_type="feedback-collector", prompt="
   DOCUMENT_ID: {doc_id}
   DOCUMENT_TYPE: PDD_DISCOVERY
   DOCUMENT_TITLE: {nombre}
   FEATURE: {feature}
   MODULO: {modulo}
   PROGRAM_SLUG: {slug}
   PERSONAS_ESPERADAS: {lista}
   ")
   ```
2. Presentar propuesta al usuario para aprobar, editar o rechazar items.
3. Items aprobados → delegar a doc-writer para actualizar tabs.
4. Cerrar loop en doc comments: `{workspace_cli} doc reply DOCUMENT_ID "{comment_id}" --content "Incorporado al discovery"`.
5. Resolver esperas: `kb espera resolve`.

---

## ESTACION: PROJECTS

Bridge a `/project`.

1. `kb project list --program {SLUG}` — listar projects del program.
2. Si existen: presentar tabla con estado. Ofrecer abrir (`/project {nombre} {modulo}`), crear nuevo o ver resumen.
3. Si no hay: los projects son soluciones concretas dentro de la oportunidad. Crear si el scope esta maduro.

### Crear project nuevo

1. Preguntar nombre del project.
2. Crear en DB:
   ```bash
   kb project create {slug} --module {MODULO} --need {NEED_SLUG} --program {SLUG} --title "{titulo}" --auto-historial
   ```
3. Delegar a doc-writer para agregar tabs de project al doc del program (usar `project_tabs` del TEMPLATE).
4. Sugerir `/project {nombre} {modulo}` para empezar a trabajarlo.

---

## ESTACION: LINEAR

1. Recomendar un barrido de consistencia si no se hizo en la sesion.
2. Validar readiness via `kb program show {SLUG} --full`.
3. Buscar doc existente: `kb doc list --program {SLUG}`.
4. Delegar a project-planner en MODO PREVIEW:
   ```
   Agent(subagent_type="project-planner", prompt="
   MODO: PREVIEW
   PROGRAM_SLUG: {slug}
   MODULE: {modulo}
   FEATURE: {feature}
   PROGRAM_DOC_ID: {si existe}
   PROGRAM_DOC_URL: {si existe}
   ")
   ```
5. Presentar preview del plan. Si el usuario aprueba → project-planner en MODO EJECUTAR.

---

## MANEJO DE ESPERAS (PARKEO)

Ver `.claude/agents/shared/espera-protocol.md` (`ENTITY_TYPE = program`).

---

## Reglas compartidas del workshop

Ver `.claude/agents/shared/workshop-shared-rules.md` (`ENTITY_TYPE = program`) — captura proactiva de errores, equipo por defecto, propagacion de completitud, tono y estilo, busqueda de contexto previo.
