# Routing Guide — Clasificacion de Input a Sub-agentes

Referencia para skills y agentes que necesitan delegar escritura al sub-agente correcto.

---

## Feedback Scope — regla canonica (SOLO definir aqui)

Esta es la fuente de verdad para distinguir los dos canales de feedback del sistema. Cualquier skill/agente que maneje feedback debe referenciar esta seccion en vez de repetir la regla.

**Canal A — Feedback SOBRE LA PLATAFORMA KB** (esta herramienta: agentes, skills, comandos `kb`, sync satellite↔core, workshops, pipelines, providers):
- Destino: `kb feedback create` → `feedback-intake` → pipeline `feedback-triager` en core
- Skill de entrada: `/soporte`
- Ejemplos: "el agente X se colgo", "me falta un skill para Y", "`/comite` no lista los issues nuevos", "el sync no trajo el ultimo feedback", "el CLI `kb` no acepta el flag Z"

**Canal B — Feedback del PRODUCTO del PM** (el sistema que el PM construye sobre la plataforma: prefacturas, conciliacion, CxC, cheques, etc.):
- Destino: `kb issue create --parent-type project|program` (si es feature/bug) o `kb question create --parent-type project|program` (si es duda de comportamiento)
- Skills de entrada: `/anota`, `/comite`, `/refinar`
- Ejemplos: "María pide que al crear etiqueta se asigne a la prefactura", "un cliente no puede exportar estado de cuenta en PDF", "duda: cuando deja de aparecer una prefactura en el EECC"

**Regla de oro:** si el feedback es sobre la herramienta con la que trabajamos, Canal A. Si es sobre el producto que el PM esta construyendo, Canal B. Ante duda, preguntar antes de capturar. **Nunca** rutear Canal B a `kb feedback create`.

---

## Tabla de Clasificacion

| Input | Sub-agente(s) | Que incluir en el prompt |
|---|---|---|
| **Notas de reunion** | `meeting-parser` → gate → `meeting-persister` + `doc-writer` (si hay decisiones de producto que actualizar en el Google Doc del program/project) + `equipo-feedback` (si hay observaciones de equipo) | Notas completas, fecha, participantes, modulo, emails resueltos via `person find`. meeting-persister ya crea tasks y questions de la reunion. |
| **Decision o dato de producto** (scope, flujo, modelo, feature) | `doc-writer` (Modo C patch) — pasar DOC_ID, TAB_ID del tab afectado (negocio/propuesta/etc.), e INSTRUCCION con el cambio. doc-writer actualiza la seccion correspondiente del Google Doc. | Que cambio, en que tab y seccion del doc, checkpoint actual. |
| **Accion o to-do concreto** | KB CLI directo: `kb todo create` | El skill ejecuta directamente. Dedup: `kb todo list --pending --module {modulo}` antes de crear. |
| **Pregunta abierta** | KB CLI directo: `kb question create` | El skill ejecuta directamente. |
| **Feedback de persona** | `equipo-feedback` | Persona, tipo de feedback, contenido, fecha |
| **Aprendizaje o framework** | `aprendizaje-writer` | Concepto, fuente, fecha, por que es relevante |
| **Hallazgo tecnico del codebase** (gap, deuda tecnica, comportamiento no documentado) | `aprendizaje-writer` | Hallazgo, repos/archivos involucrados, fecha, contexto de origen |
| **OKR o metrica** | KB CLI directo: `kb objective create` / `kb context set metricas` | El skill ejecuta directamente. |
| **Cambio organizacional** | KB CLI directo: `kb person create --upsert` / `kb team create` | El skill ejecuta directamente. |
| **Preparacion de reunion** | `meeting-researcher` → `meeting-synthesizer` | Pipeline de 2 agentes orquestado por skill /calendario PREPARA. Researcher investiga (Linear, email, chat, KB), synthesizer genera agenda + compromisos. Ambos READ-ONLY. |
| **Sync de reuniones desde calendario** | `calendar-discoverer` → `meeting-parser` → gate → `meeting-persister` | Time window, filtros. Pipeline orquestado por skill /calendario. |
| **Archivo/documento** | KB CLI directo: `kb doc register` | El skill ejecuta directamente. |
| **Documento creado/externo** (Google Doc, memo, doc externo) | KB CLI directo: `kb doc register "Nombre" "link" --tipo T --doc-id ID` | El skill ejecuta directamente. |
| **Documento template-driven o quirurgico** (crear desde KB template, ad-hoc libre, edicion celda/texto/seccion) | `doc-writer` | Modos: A (template), B (ad-hoc), C (patch). Requiere workspace provider. |
| **Program exploratorio** (necesidad de usuario, dolor, senal de mercado) | KB CLI directo: `kb program create {slug} --module {modulo} --exploratorio true` + `doc-writer` (Modo B ad-hoc, para crear el Google Doc del program con contenido inicial) | modulo, slug, problema basico, evidencia, RICE si disponible |
| **Enriquecer entidad con contexto externo** ("asocia X a mision Y", "busca info sobre Z") | 1. `external-searcher` (buscar) → 2. `doc-writer` (persistir en el tab correspondiente del Google Doc) | Flujo SECUENCIAL: leer estado actual del doc, buscar en fuentes, presentar hallazgos, consolidar y persistir via doc-writer Modo C. |
| **Research item** (pregunta a investigar, cliente a entrevistar) | KB CLI directo: `kb question create --category research` | El skill ejecuta directamente. |
| **Feedback sobre la PLATAFORMA KB** (bug en agente/skill/CLI, gap de capacidad, friccion del tooling) | `feedback-intake` | Texto del feedback, identidad del usuario de plataforma. **⚠️ Requiere confirmación explícita antes de delegar**. SOLO plataforma KB — NO feedback del producto del PM. |
| **Feedback del producto del PM** (problema, mejora, queja sobre funcionalidad del producto que el PM construye: prefacturas, conciliacion, etc.) | KB CLI directo: `kb issue create --parent-type project\|program` o `kb question create` | Describir el problema con evidencia. Rutear via `/anota`, `/comite`, o `/refinar`. NO usar feedback-intake. |
| **Resultado de analisis con ORIGEN_CONVERSACIONAL** | `meeting-parser` → `meeting-persister` PRIMERO + sub-agentes normales despues | Parsear y crear meeting primero (canal, fecha, participantes, decisiones), luego persistir resto en paralelo. |

---

## Cuando usar agente vs KB CLI directo

| Situacion | Como | Razon |
|---|---|---|
| Reuniones (notas, conversacion, sesion con personas) | `meeting-parser` → `meeting-persister` | Requiere interpretacion LLM para extraer datos estructurados |
| Acciones de una reunion | `meeting-persister` las crea | El persister ya crea tasks como parte de persistir la reunion |
| Acciones/to-dos sin contexto de reunion | KB CLI directo: `kb todo create` | CRUD simple, no necesita agente |
| Documento externo para registrar | KB CLI directo: `kb doc register` | CRUD simple |
| Cambio organizacional | KB CLI directo: `kb person create --upsert` / `kb team create` | CRUD simple |
| Pregunta abierta o research item | KB CLI directo: `kb question create` | CRUD simple |
| Resultado de analisis con origen conversacional | `meeting-parser` → `meeting-persister` PRIMERO, luego KB CLI directo | Meeting primero para vincular el resto |

**Regla clave:** Si el input tiene origen conversacional, SIEMPRE parsear y crear el meeting primero via `meeting-parser` → `meeting-persister`, luego el resto.

**Principio:** Usar agente solo cuando hay trabajo LLM (interpretar, clasificar, sintetizar). Para CRUD simple de KB, el skill ejecuta KB CLI directamente.

---

## Patrones Comunes de Multi-dominio

La mayoria de inputs tocan mas de un dominio. Lanzar sub-agentes en PARALELO salvo dependencia explicita.

**Reunion con decisiones de producto + acciones:**
→ `meeting-parser` → `meeting-persister` (nota + tasks + questions) + `doc-writer` (decisiones de producto → actualizar tab del Google Doc) — meeting primero, resto en paralelo

**Feedback de equipo que revela cambio org:**
→ `equipo-feedback` (feedback) + KB CLI directo `kb person update` / `kb team create` (mapa org) — EN PARALELO

**Decision de producto que resuelve pregunta abierta:**
→ `doc-writer` (decision → actualizar seccion del tab en Google Doc) + KB CLI directo `kb question answer` (cerrar pregunta) — EN PARALELO

**Resultado de analisis con origen conversacional:**
→ `meeting-parser` → `meeting-persister` PRIMERO, luego sub-agentes normales — SECUENCIAL: meeting primero, resto en paralelo

---

## Reglas de Delegacion

1. **Paralelismo obligatorio:** Si la info afecta varias areas, lanzar TODOS los sub-agentes en UN solo mensaje (salvo dependencia secuencial).
2. **Contexto completo:** Sub-agentes NO tienen acceso a la conversacion. Cada prompt incluye TODA la info necesaria.
3. **No explicar como:** Los sub-agentes tienen su propio conocimiento de dominio. Solo decirles QUE info nueva hay y DONDE va.
4. **Discovery directo:** Info puntual (decision, dato, cambio de scope) va directo a `doc-writer` (Modo C patch, con DOC_ID + TAB_ID + INSTRUCCION). Solo sugerir `/program para sesion estructurada de facilitacion.
5. **Que NO es accion:** Discovery, roadmap, ideas de features, exploracion → van a DB via writers. Solo son acciones las cosas concretas y ejecutables (agendar, contactar, revisar, hacer QA, enviar).
6. **Solo skills delegan a agentes:** Los agentes NO lanzan sub-agentes. Un agente usa herramientas directas (Read/Grep/KB CLI/provider CLIs). La coordinacion entre agentes es responsabilidad del skill que los invoca. Ejemplo: el skill `/project` lanza `feedback-collector`, recibe su output, presenta la propuesta al usuario, y luego lanza `doc-writer` — no es el collector quien lanza al writer.
7. **Agentes retornan datos, skills ejecutan acciones:** Los agentes producen output estructurado (reportes, propuestas, planes). Los skills se encargan de la confirmacion del usuario cuando aplica (AskUserQuestion), la ejecucion de acciones (publicar comments, enviar emails), y la coordinacion de estado (kb espera resolve).

---

## Resolucion de Contexto Antes de Delegar

ANTES de lanzar sub-agentes, resolver e incluir:
1. **IDs numericos** de programs/projects/meetings (`kb program show SLUG` → `.id`)
2. **Emails exactos** de personas mencionadas (`kb person find "{nombre}"`)
3. **Meeting ID** si se creo reunion (del output de `meeting create`)

---

## Protocolo de Dedup

Antes de delegar creacion, ejecutar checks e incluir resultados en el prompt del sub-agente:

1. **Personas:** `kb person find "{nombre}"` — si existe match exacto, pasar `--upsert`
2. **Acciones:** `kb todo list --pending --module {modulo}` — para detectar duplicados
3. **Reuniones:** `kb meeting search "{titulo}"` — para evitar duplicar registros

Formato en el prompt del sub-agente:
```
DEDUP_CONTEXT:
- person find "Carlos Gómez": [{"name": "Carlos Gómez", "email": "cgomez@empresa.com"}]
- todo list --pending: [{id: 42, text: "Revisar doc clasificadores"}]
- meeting search "standup": [{id: 5, title: "Standup Accounting", fecha: "2026-03-10"}]
```

---

## Deteccion Proactiva

### Stakeholders
Al clasificar input, identificar personas mencionadas y registrarlas:
- Solicitud de alguien → `kb todo add-stakeholder ID EMAIL --rol solicitante`
- Program/project con cliente externo → `kb program link-person SLUG EMAIL --rol cliente`
- Compromiso de reunion → `kb todo add-stakeholder ID EMAIL --rol destinatario`
- Reporte de usuario → `kb todo add-stakeholder ID EMAIL --rol reportero`

### Senales de Oportunidad
Cuando el input contenga senales de oportunidad ("los clientes piden X", "el competidor saco Y", "descubrimos que Z no funciona"), ademas de clasificar normalmente, crear el program via KB CLI (`kb program create {slug} --exploratorio true`) y lanzar `doc-writer` (Modo B) para poblar el Google Doc con la senal inicial.

---

## Patron de Routing de Skills de Pipeline

Skills que procesan issues en pipelines (`/comite`, `/refinar`, `/batman`) comparten el mismo patron de routing segun el argumento que reciben:

- **Vacio** (sin argumentos) → scan completo del backlog aplicable
- **Palabra** (ej: `receivables`) → filtra por team/modulo
- **Pattern `[A-Z]+-[0-9]+`** (ej: `AR-1910`) → single-issue, salta directo a la accion

**Flujo operativo del pipeline:**

```
Triage → /comite (decide destino) → Backlog → /refinar (dev-ready) → To do → /batman (fix rapido)
```

Cada skill en este flujo asume que el anterior ya procesó su estacion:
- `/comite`: clasifica y decide destino (Backlog, cancelar, crear program/project, consolidar)
- `/refinar`: completa contexto tecnico, acceptance criteria, edge cases — lo deja dev-ready
- `/batman`: workshop para fix rapido end-to-end (issue → analisis → dev → publicar)
