---
name: cierra
domain: core
description: "Sweep de cierre de sesion. Propaga fixes de plataforma, detecta optimizaciones operativas y valida tests acotados al scope impactado (o suite completa si tocas infra transversal). Modos: --solo-plataforma, --solo-ops, --sin-tests, --full-tests."
---

Eres el skill `/cierra` — un sweep de cierre de sesion que tiene tres responsabilidades:

1. **Propagacion de plataforma:** detectar y aplicar fixes en todos los archivos afectados cuando se modificaron archivos de cualquier capa (`.claude/`, `backend/`, `tools/`, `platform/`, root configs)
2. **Optimizacion operativa:** analizar archivos modificados y proponer mejoras (consolidacion CLI, deduplicacion, friccion, code patterns)
3. **Validacion de tests:** generar, modificar o eliminar tests segun los cambios de codigo y correr las suites impactadas (o full-suite cuando toca infra transversal) para verificar que nada regresiono

## Invocacion

```
/cierra                      # Sesion completa (plataforma + ops + tests acotados)
/cierra --solo-plataforma    # Solo Fases 1-2 (propagacion)
/cierra --solo-ops           # Solo Fases 1 + 2.5 (scan + optimizacion)
/cierra --sin-tests          # Sesion completa pero saltea Fase 3 (tests)
/cierra --full-tests         # Fuerza suite completa ignorando el scope resuelto en 3C
```

---

## FASE 1 — SCAN DE SESION

Dos tareas: detectar archivos modificados + compilar resumen de sesion.

### 1A. Archivos modificados

```bash
git diff --name-only HEAD        # Cambios sin commitear
git status --short               # Archivos con estado
```

Si hay commits recientes (sesion larga):
```bash
git log --oneline -10            # Ver ultimos 10 commits
git diff --name-only HEAD~5 HEAD # Archivos modificados en ultimos 5 commits
```

**Clasificar archivos detectados:**

| Tipo | Patron | Accion |
|------|--------|--------|
| Plataforma (.claude) | `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, `.claude/settings.json`, `.claude/agents/shared/*` | Fase 2 + Fase 2.5 |
| Backend | `backend/apps/*/models.py`, `*/serializers.py`, `*/views.py`, `*/urls.py`, `*/services/*.py`, `*/migrations/*.py`, `*/tests/*.py` | Fase 2 |
| Tools | `tools/*/cli.py`, `tools/*/commands/*.py`, `tools/*/client/*.py`, `tools/*/provider.md`, `tools/*/permissions.txt` | Fase 2 + Fase 2.5 |
| Frontend | `platform/src/**/*.ts`, `platform/src/**/*.tsx` | Fase 2 |
| Root configs | `CLAUDE.md`, `docker-compose*.yml`, `.mcp.json`, `pyproject.toml` | Fase 2 |
| Otros | cualquier otro (`docs/`, `deploy/`, `runner/`, etc.) | Mencionar en reporte, no propagar |

**Extraer terminos clave:**

Para cada archivo modificado, extraer los 3-5 terminos mas distintivos usando heuristicas por capa:

- **`.claude/`**: nombres de conceptos, reglas, patrones de comportamiento, nombres de agentes/skills
- **`backend/models.py`**: class names, field names (`models.XXXField`), related_name values
- **`backend/serializers.py`**: serializer class names, Meta.model refs, field lists
- **`backend/views.py`**: viewset names, queryset model refs, action names
- **`backend/urls.py`**: path patterns, URL names
- **`tools/*/commands/*.py`, `tools/*/cli.py`**: command names (`@app.command`), endpoint paths, flags
- **`platform/src/lib/kb-api.ts`**: function names, fetch URL patterns
- **`platform/src/**/*.tsx`**: component names, imported API functions
- **`CLAUDE.md`**: section headings, directivas clave
- **Root configs**: service names, tool names, dependency names

Estos terminos se pasan al cierre-scanner.

### 1B. Resumen de sesion

Revisar la conversacion para compilar:

1. **MCP tools usados:** Identificar invocaciones de MCP tools (patron `mcp__*`). Compilar lista con `{tool_name, count, context}` — context es una descripcion breve de para que se uso.
2. **Agentes invocados:** Listar sub-agentes lanzados durante la sesion con `{agent_name, task_summary, approximate_steps, issues_observed}` — approximate_steps es estimado del resultado, issues_observed son patrones como reintentos, over-fetching, roundtrips excesivos.
3. **Patrones de proceso:** Notar si algun agente requirio multiples rondas, reintentos, o pasos redundantes.
4. **CLIs modificados:** Si Fase 1A detecto `tools/*/cli.py` modificados, extraer los comandos nuevos/cambiados:
   - Correr `git diff HEAD -- tools/*/cli.py` y buscar funciones nuevas (lineas `+def ` o `+@app.command`)
   - O comparar `--help` output si el diff es grande
   - Compilar lista: `{cli_name, new_commands: ["cmd1", "cmd2"], changed_commands: ["cmd3"]}` — esto se pasa al ops-scanner en Fase 2.5

### 1C. Decision de fases

**Si no hay archivos de plataforma/backend/tools/frontend modificados Y session_mcp_usage esta vacio Y session_agent_traces no tiene issues:**
- Si `--solo-plataforma`: terminar con "Sin cambios de plataforma en la sesion."
- Si `--solo-ops`: terminar con "Sin cambios en archivos de plataforma ni anti-patterns de sesion — optimizacion no aplica."
- Si sesion completa: saltar Fase 2 y 2.5, ir directamente a Fase 4

**Short-circuit de Fase 2 — migraciones DDL puras.** Si TODOS los archivos modificados son `backend/apps/*/migrations/NNNN_*.py` cuyo contenido es exclusivamente `RunSQL(...)` con DDL (`DROP/ALTER/CREATE TABLE|COLUMN|INDEX|CONSTRAINT`, sin `RunPython`, sin cambios en `models.py`/`serializers.py`/`views.py`/CLIs/agentes/skills), saltar Fase 2 directamente a Fase 2.5 con: "Fase 2 — migraciones DDL puras, scan de propagacion no aplica (el schema no afecta codigo)". Las migraciones DDL son auto-contenidas: no introducen conceptos nuevos ni renombran entidades que referencien otros archivos.

Mostrar al usuario:
```
FASE 1 — SCAN
Archivos modificados por capa:
  .claude/: N archivos
    - .claude/agents/ejemplo.md
    - CLAUDE.md
  backend/: M archivos
    - backend/apps/core/models/content.py
    - backend/apps/core/serializers/content.py
  tools/: K archivos
    - tools/kb/commands/document.py
  platform/: J archivos
    - platform/src/lib/kb-api.ts
  root configs: I archivos
  otros: L archivos (no requieren propagacion)
Terminos extraidos: "termino1", "termino2", "termino3"
CLIs de providers modificados: K
  - metabase: +16 comandos (dashboard copy, card list, search, ...)
Sesion:
  MCP tools usados: mcp__claude_ai_Linear__save_project (7x), kb figma metadata (2x)
  Agentes invocados: doc-writer (1x, ~15 tool calls), project-planner (1x, ~8 tool calls)
  Patrones detectados: MCP usage where CLI exists, over-fetching en doc-writer
```

---

## FASE 2 — PROPAGACION ITERATIVA

Si `--solo-ops`: saltear esta fase, ir a Fase 2.5.

La propagacion corre en loop hasta convergencia. Maximo 5 rondas (evita loops infinitos).

### Estado del loop

Mantener en memoria durante la fase:
```
round: 1
all_terms: [terminos extraidos en Fase 1]
already_scanned: []
modified_files: [archivos modificados de todas las capas]
all_fixes_found: []    # acumulado de todas las rondas
total_fixes_applied: 0
```

### Loop: ejecutar hasta convergence = true o round > 5

**Por cada ronda:**

1. **Invocar cierre-scanner** con:
   ```
   modified_files: [archivos ya modificados + archivos recien fixeados]
   terms: [terminos de esta ronda — los nuevos descubiertos en ronda anterior]
   already_scanned_terms: [todos los terminos ya escaneados]
   round: N
   session_context: "..."
   ```

   El scanner usa su mapa de propagacion interno para determinar donde buscar segun la capa de cada archivo modificado.

2. **Mostrar progreso de la ronda** al usuario:
   ```
   Ronda N — escaneando: "termino1", "termino2"
   -> N fixes encontrados en M archivos (K cross-layer) | J legacy | I diferente contexto
   -> Terminos nuevos para ronda N+1: "termino-nuevo-A", "termino-nuevo-B"
   ```

3. **Si `propagation_needed` tiene items:**

   Gate con AskUserQuestion (solo en la primera ronda que encuentre fixes, luego aplicar automaticamente si el usuario eligio "todos"):

   ```yaml
   question: "Ronda 1: encontre N fixes. Como proceder?"
   options:
     - label: "Aplicar todos y continuar escaneando (Recommended)"
       description: "Aplica estos N fixes y sigue buscando hasta convergencia"
     - label: "Revisar uno por uno en cada ronda"
       description: "Te muestro cada fix antes de aplicarlo, en todas las rondas"
     - label: "Aplicar estos N y detener el scan"
       description: "Aplica la ronda actual y no continua buscando"
     - label: "Saltar propagacion"
       description: "Ir al reporte de consolidacion"
   ```

   **Aplicar fixes aprobados** via `Edit` tool:
   - Para cada item en `propagation_needed` aprobado: `Edit` con `old_string = current_text`, `new_string = proposed_fix`
   - Agregar los archivos recien editados a `modified_files` para la proxima ronda
   - Acumular en `all_fixes_found`

4. **Actualizar estado del loop:**
   - `already_scanned` += terminos de esta ronda
   - `all_terms` += `next_round_terms` del resultado
   - Proxima ronda usa solo los `next_round_terms` como `terms` (los ya escaneados van a `already_scanned`)

5. **Condicion de parada:**
   - `convergence: true` en el resultado del scanner -> terminar loop
   - O `round > 5` -> terminar con advertencia

### Despues del loop

Mostrar resumen:
```
FASE 2 — PROPAGACION COMPLETADA
Rondas ejecutadas: N
Total fixes aplicados: M en K archivos
  - .claude/: X fixes
  - backend/: Y fixes
  - tools/: Z fixes
  - platform/: W fixes
Convergencia: alcanzada en ronda N / maximo de rondas alcanzado (revisar manualmente)
Legacy intencional: J matches (no modificados)
Diferente contexto: I matches (no modificados)
```

Si desde la primera ronda `propagation_needed` estuvo vacio y `convergence: true`:
```
FASE 2 — Sin propagacion pendiente (convergencia en ronda 1).
```

-> En ambos casos continuar a Fase 2.5.

---

## FASE 2.5 — OPTIMIZACION OPERATIVA

Si `--solo-plataforma`: saltear esta fase, ir a Fase 4.

**Trigger:** Se cumple CUALQUIERA de estas condiciones:
- FASE 1 encontro archivos en `.claude/agents/` o `.claude/skills/` modificados
- FASE 1 encontro archivos en `backend/` modificados
- FASE 1 encontro archivos en `platform/` modificados
- FASE 1 encontro archivos en `tools/` modificados
- `session_mcp_usage` no esta vacio (se usaron MCP tools en la sesion)
- `session_agent_traces` tiene items con `issues_observed` no vacio
- FASE 1 encontro CLIs de providers modificados (`tools/*/cli.py`, `tools/*/permissions.txt`)

Si ninguna condicion se cumple y no se paso `--solo-ops` -> saltar con "Sin cambios en archivos de plataforma ni anti-patterns de sesion — optimizacion no aplica."

**Pasos:**

1. Invocar `ops-scanner` (Agent tool, subagent_type="ops-scanner") con:
   ```
   modified_agents: [agentes detectados en FASE 1]
   modified_skills: [skills detectados en FASE 1]
   modified_tools: [{cli_name, new_commands, changed_commands}]  # De FASE 1B.4
   modified_backend: [archivos backend detectados en FASE 1]
   modified_frontend: [archivos frontend detectados en FASE 1]
   session_context: "descripcion del trabajo realizado en la sesion"
   session_mcp_usage: [{tool_name, count, context}]  # De FASE 1B
   session_agent_traces: [{agent_name, task_summary, approximate_steps, issues_observed}]  # De FASE 1B
   ```

2. Si `optimizations` tiene items, mostrar reporte:
   ```
   FASE 2.5 — OPTIMIZACION OPERATIVA

   HIGH:
   - OPT-001: {title}
     Archivo: {affected_files}
     Propuesta: {proposed_improvement}
   MEDIUM:
   - OPT-002: {title}
     Archivo: {affected_files}
     Propuesta: {proposed_improvement}
   ```

3. Gate con AskUserQuestion:
   ```yaml
   question: "N optimizaciones detectadas. Como proceder?"
   options:
     - label: "Aplicar high-impact (Recommended)"
       description: "Aplica fixes directamente en los archivos afectados (solo impacto alto)"
     - label: "Aplicar todas"
       description: "Aplica todos los fixes directamente"
     - label: "Solo ver reporte"
       description: "Ya vi el reporte, no aplicar cambios"
     - label: "Saltar"
       description: "Ignorar optimizaciones"
   ```

4. Para las optimizaciones aprobadas, aplicar fixes directamente via Edit tool en los archivos afectados (`affected_files`). Si el output incluye `exact_old_string` y `exact_new_string`, usarlos directamente. Si no, usar `current_pattern` para localizar el codigo a cambiar y `proposed_improvement` como guia del fix.

5. Reportar N fixes aplicados en M archivos.

Si `optimizations` esta vacio:
```
FASE 2.5 — Sin optimizaciones detectadas en los archivos modificados.
```

-> Continuar a Fase 3.

---

## FASE 3 — TESTS

Si `--solo-plataforma`, `--solo-ops` o `--sin-tests`: saltear esta fase, ir a Fase 4.

**Trigger:** Fase 1 detecto archivos en alguno de estos patrones:
- `backend/apps/**/*.py` (cualquier archivo de app: models, serializers, views, services, urls, migrations, tests, conftest, factories)
- `backend/conftest.py`, `backend/settings.py`, `backend/manage.py`, `backend/pyproject.toml`
- `tools/kb/**/*.py`, `tools/kb/pyproject.toml`

Si no hay triggers (solo se tocaron `.claude/`, `platform/`, docs, o tools sin tests), reportar "Fase 3 — Sin cambios de codigo que requieran tests." y continuar a Fase 4.

### 3A — Diff → plan de tests

Para cada archivo de codigo modificado, detectar su test asociado y clasificar el cambio requerido:

| Heuristica de correspondencia |
|---|
| `backend/apps/{app}/X.py` ↔ `backend/apps/{app}/tests/test_X.py` |
| `backend/apps/{app}/services/X.py` ↔ `backend/apps/{app}/tests/test_X_service.py` (o similar) |
| `tools/{tool}/commands/X.py` ↔ `tools/{tool}/tests/test_X.py` o `tools/{tool}/tests/test_integration/test_X.py` |
| `tools/{tool}/cli.py` / `client/*.py` ↔ tests del mismo tool |

Revisar el diff (`git diff HEAD -- PATH`) para cada archivo de codigo y clasificar:

- **`add`**: aparece funcion/clase/comando/endpoint/serializer nuevo sin cobertura → proponer caso o archivo nuevo
- **`update`**: cambio de firma, shape de response, regla de negocio, validacion → proponer edicion del test existente
- **`delete`**: se removio funcionalidad → proponer borrado del caso o del archivo de test

**Antes de proponer un test nuevo:** leer un test vecino del mismo directorio para capturar convenciones (fixtures, naming, factories, parametrize patterns). No inventar estilo.

Mostrar plan al usuario:
```
FASE 3 — TESTS (plan)
  add: N archivos/casos nuevos
    - backend/apps/core/tests/test_foo_service.py (nuevo, cubre foo_service.calcular)
    - tools/kb/tests/test_report.py::test_download_variant (caso nuevo)
  update: M casos a editar
    - backend/apps/crm/tests/test_opportunity.py::test_serialize (cambio de campo)
  delete: K a borrar
    - backend/apps/erp/tests/test_legacy_flow.py (funcionalidad removida)
```

### 3B — Gate + aplicar

```yaml
question: "Plan de tests: A nuevos, U editados, D borrados. Como proceder?"
options:
  - label: "Aplicar todo (Recommended)"
    description: "Crea/edita/borra segun el plan"
  - label: "Revisar uno por uno"
    description: "Gate individual por cada cambio de test"
  - label: "Solo generar, no eliminar"
    description: "Aplica add y update, omite deletes (conservador)"
  - label: "Saltar y correr suite tal cual"
    description: "No toca tests, va directo a 3C con lo que haya"
```

Aplicar segun accion:
- `add` → `Write` (archivo nuevo) o `Edit` (caso nuevo en archivo existente)
- `update` → `Edit`
- `delete` → `Bash rm PATH` (archivo completo) o `Edit` para borrar un caso

### 3C — Resolver scope de tests

Si el usuario paso `--full-tests`: scope = full-suite, saltar la clasificacion y correr todo.

Si no, clasificar cada archivo modificado de Fase 1A aplicando reglas en este orden (la primera que matchee gana para ese archivo):

**1. Trigger full-suite** (cualquier match en CUALQUIER archivo → correr todo el backend):

- `backend/conftest.py`, `backend/settings.py`, `backend/manage.py`
- `backend/pyproject.toml`, `backend/*.cfg`, `backend/*.ini`
- `backend/apps/core/**` (foundation — 79 imports cross-app)
- `backend/apps/*/migrations/*.py` **que contenga `RunPython`** (DDL puro ya esta short-circuited en Fase 1C; aca queda migracion con logica Python → correr todo)
- `backend/apps/*/tests/conftest.py`, `backend/apps/*/tests/factories*.py`
- `.env*`, `docker-compose*.yml` que cambien servicios DB/test

Si matchea, el backend corre completo y se ignoran las reglas 2 para ese set. Las reglas de tools (regla 3) se evaluan aparte.

**2. Hub apps — fan-out definido** (agregar las apps que los importan):

| App tocada | Suites backend a correr |
|---|---|
| `backend/apps/workflow/**` | `apps/workflow/tests apps/workforce/tests apps/sync/tests apps/providers/tests` |
| `backend/apps/providers/**` | `apps/providers/tests apps/sync/tests apps/channels/tests` |
| `backend/apps/sync/**` | `apps/sync/tests` |
| `backend/apps/workforce/**` | `apps/workforce/tests` |
| `backend/apps/channels/**` | `apps/channels/tests` |
| `backend/apps/pms/**` | `apps/pms/tests` |
| `backend/apps/crm/**`, `apps/erp/**`, `apps/bi/**`, `apps/notifications/**`, `apps/workshop/**` | — (no tienen tests; reportar "app sin tests") |

La union de los scopes de cada archivo modificado es el set final.

**3. Tools — aislado**:

- `tools/kb/conftest.py` o `tools/kb/pyproject.toml` → full de `tools/kb`
- Cualquier otro cambio bajo `tools/kb/**` → `tools/kb` tests
- Otros `tools/*` → no tienen tests, reportar

**Mostrar scope resuelto al usuario** (informativo, sin gate):

```
FASE 3C — SCOPE DE TESTS
  Archivos tocados: N
  Scope backend: [full-suite | impactado]
  Razon: "apps/workflow tocado → fan-out a workforce, sync, providers"
  Suites a correr:
    - backend: apps/workflow/tests apps/workforce/tests apps/sync/tests apps/providers/tests
    - tools/kb: (sin cambios, skip)
  Equivalente full-suite: NO
```

### 3C — Ejecutar suites seleccionadas

Backend con scope acotado:
```bash
cd backend && pytest {lista de dirs} --tb=short
```

Backend full-suite:
```bash
cd backend && pytest --tb=short
```

Tools:
```bash
cd tools/kb && pytest --tb=short
```

Mostrar resultado por suite:
```
FASE 3C — RESULTADOS
  backend (impactado):  PASS 87  / FAIL 0
  tools/kb (skip):      —
```

### 3D — Iterar si hay fallos (max 3 intentos)

Si alguna suite tiene `FAIL > 0`:

1. Mostrar el primer fallo con stack compacto (`pytest` ya lo devuelve con `--tb=short`)
2. Gate con AskUserQuestion:
   ```yaml
   question: "Intento N/3 — fallo en {suite}::{test}. Como proceder?"
   options:
     - label: "Arreglar test (Recommended)"
       description: "El cambio de codigo es correcto, el test quedo desalineado — edito el test"
     - label: "Arreglar codigo"
       description: "El test esta bien, el cambio introdujo un bug — edito el codigo"
     - label: "Marcar como pre-existente (skip)"
       description: "Este fallo no es mio, ya estaba roto — lo registro como deuda y sigo"
     - label: "Abortar cierra"
       description: "No puedo arreglarlo ahora, detener /cierra sin llegar a Fase 4"
   ```
3. Si el usuario elige arreglar: aplicar fix via `Edit`, re-correr la misma suite afectada, volver a 3D
4. Si elige skip: registrar `{suite, test, razon: pre-existente}` en la lista de deuda y continuar a la siguiente
5. Al alcanzar 3 intentos sin convergencia: advertencia y continuar a Fase 4 con `tests_status: failed` y la lista de fallos sin resolver

### Salida

Mostrar:
```
FASE 3 — TESTS COMPLETADO
  Cambios aplicados: X nuevos, Y editados, Z borrados
  Suites corridas: N
  Resultado: PASS / FAIL
  Intentos de fix: K
  Deuda marcada: [lista de tests pre-existentes rotos]
```

-> Continuar a Fase 4.

---

## FASE 4 — CONSOLIDACION

Reporte final:

```
CIERRE DE SESION — COMPLETADO

Propagacion de plataforma:
  N fixes aplicados en M archivos (R rondas hasta convergencia)
  - .claude/: X fixes
  - backend/: Y fixes
  - tools/: Z fixes
  - platform/: W fixes
  - K matches legacy (no modificados)
  - J matches diferente contexto (no modificados)
  [ADVERTENCIA si round > 5: convergencia no alcanzada, revisar manualmente]

Optimizacion operativa:
  N optimizaciones detectadas, M aplicadas
  - K sin cambios (no aplicadas)

Tests:
  Scope: [impactado | full-suite | forzado con --full-tests]
  Cambios: X nuevos, Y editados, Z eliminados
  Suites corridas: {lista}
  Resultado: PASS / FAIL (M tests rotos)
  Intentos de fix: K
  Deuda pre-existente: [lista de tests marcados como skip]
  [ADVERTENCIA si tests_status == failed: no se alcanzo convergencia en 3 intentos]
  [NOTA si scope == impactado: "Scope acotado — si sospechas regresiones fuera del mapeo, correr /cierra --full-tests"]

Pendientes para proxima sesion:
  - [lista de items que quedaron sin resolver]
```

Si todo estuvo limpio:
```
Sesion limpia — convergencia alcanzada en ronda 1, sin optimizaciones pendientes, suite PASS.
```

---

## REGLAS

1. **Gates siempre antes de escribir** — nunca aplicar fixes sin aprobacion explicita
2. **cierre-scanner es READ-ONLY** — solo el MAIN agent (este skill) aplica los Edit
3. **Sesion completa vs modos:** respetar el flag de invocacion (`--solo-plataforma`, `--solo-ops`, `--sin-tests`)
4. **Si cierre-scanner no encuentra nada:** reportarlo positivamente y avanzar a Fase 2.5
5. **Tono:** conciso, orientado a accion. Español. Sin markdown decorativo en los reports.
6. **ops-scanner es READ-ONLY** — solo el MAIN agent aplica fixes directamente con aprobacion del usuario.
7. **Tests son obligatorios cuando el trigger aplica** — si Fase 1 detecto cambios en `backend/apps/*/{models,serializers,views,services,urls}.py` o `tools/*/{commands,cli,client}/*.py`, Fase 3 DEBE correr. Solo la saltean los flags `--solo-plataforma`, `--solo-ops` o `--sin-tests` (explicitos del usuario). Nunca omitir Fase 3 sin flag.
8. **Scope de tests impactado** — Fase 3C resuelve que suites correr segun los archivos tocados. Cambios en `apps/core/**`, `conftest.py`, `settings.py`, `pyproject.toml` o migraciones con `RunPython` → full-suite. Hub apps (workflow, providers) → fan-out definido. Tools aislados. Flag `--full-tests` fuerza suite completa. Trade-off asumido: el mapeo no cubre dependencias implicitas (helpers compartidos fuera de las reglas) — si el usuario sospecha que el scope quedo corto, usa `--full-tests`.
9. **Seguir convenciones del directorio al generar tests** — leer un test vecino del mismo directorio antes de escribir uno nuevo (fixtures, naming, factories, parametrize patterns). No inventar estilo propio.
10. **Fallos pre-existentes** — si el usuario los marca como skip en 3D, registrarlos en el reporte final de Fase 4 como deuda explicita; nunca ocultarlos ni mezclarlos con los PASS.
