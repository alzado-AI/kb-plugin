---
name: actualiza
domain: core
description: "Auditoria de documentos KB. Detecta referencias deprecadas a skills/agentes y propone actualizaciones. Sin argumentos: audita todo. Con nombre: /actualiza solucion."
disable-model-invocation: false
---

Auditoria y actualizacion de la base de conocimiento del producto.

## Entrada

- `$ARGUMENTS` vacio → auditar todos los docs KB contra todos los skills/agentes
- `$ARGUMENTS` = nombre de skill o agente (ej: "solucion", "doc-writer") → auditar solo docs que mencionan ese skill/agente

## KB CLI (validacion alternativa)

Si el CLI `kb` esta disponible, usarlo para validacion estructural:
```bash
kb status                          # Conteos generales
kb query gaps                      # Objectives sin programs, programs sin need, programs sin projects
kb todo list --pending           # Acciones pendientes
```

El CLI complementa con validacion relacional (FKs, gaps entre entidades).

---

## FASE 1 — Inventario del sistema (fuente de verdad)

Leer en paralelo todos los archivos de definicion del sistema:

```
Glob: .claude/skills/*/SKILL.md        → lista de skills con su contenido
Glob: .claude/agents/*.md              → lista de agentes con su contenido
```

Para cada archivo, extraer:
- Nombre del skill/agente
- Comportamiento principal (primeras 40 lineas + secciones INPUT/OUTPUT/FASE)
- Cualquier cambio documentado explicitamente

Si `$ARGUMENTS` especificado: leer solo el SKILL.md o agente que coincida con el nombre dado.

### 1b. Historial de renames y eliminaciones

Ejecutar:
```
git log --oneline --diff-filter=RD --name-status -- '.claude/skills/' '.claude/agents/'
```

Esto genera un mapa de cambios historicos:
- **Renames (R):** nombre_viejo → nombre_nuevo (ej: `ciclo/SKILL.md` → `solucion/SKILL.md`)
- **Deletes (D):** nombre eliminado (ej: `pdd-writer.md` — consolidado en otro agente)

Para cada rename, extraer:
- Nombre viejo del skill/agente (ej: `ciclo`, `producto-writer`)
- Nombre nuevo (ej: `solucion`, `issue-writer`)
- Patrones de archivo derivados del nombre viejo:
  - `.{nombre-viejo}-estado.md` (archivos de estado)
  - `/{nombre-viejo}` (referencias a skill con slash)
  - `{nombre-viejo}` (menciones en prosa)

Para cada delete, extraer:
- Nombre eliminado (ej: `pdd-writer`)
- Commit message para contexto (ej: "consolidado en doc-writer")

### 1c. Estado canonico (DB)

El estado de programs y projects vive en la DB (no en filesystem). Verificar que los skills/agentes referencien correctamente:
- Estado operativo: `kb program show SLUG --full` / `kb project show SLUG --full`
- Gates: `kb gate list --program SLUG` / `kb gate list --project SLUG`
- Esperas: `kb espera list --program SLUG` / `kb espera list --project SLUG`
- Pipeline: `kb query pipeline-status`

Si algun skill/agente todavia referencia `.project-estado.md`, `.program-estado.md`, `index.md de programs, rutas `kb/producto/`, `kb/gestion/`, o `kb/archivos/`, clasificar como **DEPRECADO**.

## FASE 2 — Scan del KB

Ejecutar las tres categorias en paralelo.

### 2a. Referencias de comportamiento (Categoria A)

**Siempre leer:**
```
Read: CLAUDE.md
```

**Grep en candidatos** (solo estos — son los unicos que pueden describir behaviors):
```
Grep pattern="/{skill}" o pattern="{agente}" en:
  - `kb learning search "{skill}"` — busca en aprendizajes
→ retener solo archivos con menciones reales
```

Si `$ARGUMENTS` especificado: grep solo por ese skill/agente.

**Excluir del scan** (son datos/contenido, no behavior descriptions):
- discoveries de features (viven en DB, no en filesystem)
- acciones (via `kb todo list`) — to-dos
- preguntas (via `kb question list`) — preguntas abiertas
- reuniones (via `kb meeting list`) — notas historicas
- personas (via `kb person list`) — perfiles de personas
- equipos (via `kb team list`) — relaciones persona-feature-equipo
- `apps/`, `kb/archivos/` — codigo, binarios

### 2b. Estado operativo activo (Categoria B)

Consultar estado de programs y projects activos via DB:

```bash
kb query pipeline-status              # Programs/projects por estacion
kb query active-esperas               # Esperas sin resolver
kb program list --estado activo         # Programs activos
kb project list                       # Projects con estado
```

Para cada program/project activo con estacion asignada, extraer:
- `estacion` actual
- `sub_posicion`
- `bloqueado`
- Esperas via `kb espera list --program SLUG` / `--project SLUG`

**Deteccion de archivos deprecados (usa mapa de FASE 1b + 1c):**

Grep en skills y agentes por referencias a archivos que ya no existen:
```
Grep pattern="\.project-estado\.md|\.program-estado\.md|\.estado-project\.md|\.estado-program\.md" en:
  - .claude/skills/*/SKILL.md
  - .claude/agents/*.md
```

Tambien grep por referencias al skill viejo con slash:
- `/{nombre-viejo}` — referencias al skill con slash
- `{nombre-viejo}` en contexto de skill/agente (no usos naturales de la palabra)

Para cada referencia deprecada encontrada:
- Leer contexto
- Contar referencias
- Clasificar como **DEPRECADO** con propuesta de actualizacion a CLI

Determinar skills/agentes relevantes por estacion:
- PROBLEMA/INVESTIGACION/DIAGNOSTICO/DERIVACION → `/analiza`
- DISCOVERY → `/program (estacion DISCOVERY)), `doc-writer`
- DOCUMENTO → `doc-writer` (escribe directamente al Google Doc del program/project)
- FEEDBACK → `/program (estacion FEEDBACK)), `feedback-solicitor`, `feedback-collector`
- PROTOTIPO → `/project` (estacion PROTOTIPO), `app-builder`
- DISENO → `/project` (estacion DISENO), `design-reader`
- PROJECTS → `/program` (estacion PROJECTS)
- LINEAR → `/program (estacion LINEAR)), `project-planner`
- DEV → `/project` (estacion DEV), `issue-analyzer`, `code-implementer`, `code-reviewer`, `code-publisher`
- TICKET → `/batman`

Si `$ARGUMENTS` especificado: solo procesar estados cuya estacion sea relevante para ese skill/agente.

### 2c. Conformidad de datos (Categoria C)

En paralelo:

**Programs activos (completitud de contenido):**
```bash
kb program list --estado activo       # Programs activos
# Para cada program activo:
kb program show SLUG --full           # Incluye content bodies
```

Verificar content types esperados contra el template:
```bash
kb template show program-discovery --read-base-file
```
Extraer los tabs declarados en `base_file_content` (program-level y `project_tabs` para projects) y comparar contra los content types presentes en cada program/project via `kb project show SLUG --full`. **No hardcodear la lista — el template es la fuente de verdad.** Si un tab declara `required: true` (o equivalente en el scaffold) y la entidad no lo tiene, flaggearlo.

**Acciones:**
```bash
kb todo list --pending            # Acciones pendientes
kb team list                        # Modulos registrados
# Comparar: modulos con acciones vs modulos registrados
```

**Perfiles de equipo** (solo si `$ARGUMENTS` vacio — auditoria completa):
```bash
kb person list                      # Lista de personas con modulos
# Para cada persona: verificar que tenga datos completos (rol, modulo)
```

### 2d. Conformidad estructural DB (Categoria D)

Validar consistencia relacional via DB:

```bash
kb query gaps                        # Objectives sin programs, programs sin need, programs sin projects, etc.
kb lint check --pretty               # Reglas de consistencia DB
```

Para cada program activo:
1. Verificar que tenga: modulo asignado, al menos 1 project si estacion >= PROJECTS

Para cada project activo:
1. Verificar que tenga: program asignado, escala definida
2. Si estacion DEV: verificar workspace_path definido
3. Verificar esperas activas > 14 dias (posible bloqueo olvidado)

## FASE 3 — Analisis de inconsistencias

### Categoria A (referencias de comportamiento)

Para cada doc con menciones:
1. Leer el contexto alrededor de cada mencion (seccion completa)
2. Comparar con el comportamiento actual del skill/agente (FASE 1)
3. Clasificar:
   - **DESACTUALIZADO** — el doc dice X pero el skill ahora hace Y
   - **FALTANTE** — el skill tiene capacidad nueva no documentada en el KB
   - **OBSOLETO** — el doc menciona algo que ya no existe en el skill
   - **OK** — alineado

### Categoria B (estado operativo)

Para cada program/project con estacion asignada:
1. Identificar la estacion/posicion actual (de DB)
2. Para cada skill relevante a esa estacion, comparar el comportamiento actual (FASE 1) contra lo que el estado asume
3. Si hay cambios de comportamiento relevantes:
   - Clasificar como **AVISO**
   - Generar texto contextual: que cambio, como afecta la sesion en curso, que verificar
   - Ejemplos de cambios que generan aviso:
     - Nuevo triage de complejidad antes de TRACK:Redactar
     - Nueva opcion en gate (ej: spec ligera disponible)
     - Cambio en formato de salida del agente
4. Si se encontraron skills/agentes con referencias a archivos de estado deprecados (FASE 2b):
   - Clasificar como **DEPRECADO**
   - Proponer: actualizar referencia a usar CLI en vez de filesystem

### Categoria C (conformidad de datos)

Para cada program/project con datos incompletos:
1. Comparar content types presentes vs requeridos segun estacion actual
2. Clasificar como **CONTENIDO_FALTANTE** si faltan content types requeridos
3. Programs/projects completados: NO chequear (son historico)
4. Para acciones: flag por modulo sin acciones o acciones sin modulo valido
5. Para personas: flag por persona sin rol o sin modulo asignado

### Categoria D (conformidad estructural DB)

Para cada hallazgo de `query gaps` o `lint check`:
1. Clasificar segun tipo:
   - **RELACION_FALTANTE**: program sin objective, program sin need, project sin program, etc.
   - **CAMPO_FALTANTE**: program activo sin estacion, project DEV sin workspace_path
   - **ESPERA_VENCIDA**: espera activa > 14 dias sin resolver
   - **GATE_PENDIENTE**: gate de estacion anterior aun pendiente
2. Proponer correccion via CLI

## FASE 4 — Gate — Preview de cambios propuestos

Mostrar con AskUserQuestion. Separar por tipo:

```
AUDITORIA KB — {scope: "todo" | nombre del skill/agente}

=== A. REFERENCIAS DE COMPORTAMIENTO ===
Docs revisados: {N} | Con cambios propuestos: {M} | OK: {K}

{para cada inconsistencia}
[DESACTUALIZADO|FALTANTE|OBSOLETO] {path/to/doc.md}
  Dice:    "{texto actual en el doc}"
  Ahora:   "{comportamiento real del skill}"
  Propone: "{texto sugerido}"

=== B. ESTADO OPERATIVO (DB) ===
Programs/projects con estacion: {N}

{para cada estado con aviso}
[AVISO] {program_slug o project_slug}
  Posicion: {estacion}:{sub_posicion} | Bloqueado: {si/no}
  Cambio:  {descripcion del cambio en skill relevante}

{si no hay avisos}
Sin cambios relevantes para los estados activos.

=== REFS DEPRECADAS (archivos estado filesystem) ===
Skills/agentes con refs a archivos .estado: {N}

{para cada skill/agente con refs deprecadas}
[DEPRECADO] {path/SKILL.md o agente.md}
  Refs: {N} menciones a ".project-estado.md" / ".program-estado.md" / "index.md"
  Propone: actualizar a usar CLI (program show --full, project show --full)

=== C. CONFORMIDAD DE DATOS ===
Programs activos: {N} | Con contenido faltante: {M} | OK: {K}
Projects activos: {N} | Con contenido faltante: {M} | OK: {K}
Acciones: {OK | N inconsistencias}
Perfiles equipo: {N checkeados} | Con problemas: {M} | OK: {K}

{para cada CONTENIDO_FALTANTE}
[CONTENIDO_FALTANTE] program:{slug} o project:{slug}
  Estacion: {estacion} | Falta: {lista de content types faltantes}
  Propone: crear contenido via `doc-writer` (delegar escritura al Google Doc del program/project)

{si todo OK en C}
Datos conformes en todas las entidades revisadas.

=== D. CONFORMIDAD ESTRUCTURAL DB ===
Hallazgos de `query gaps` + `lint check`: {N}

{para cada hallazgo}
[RELACION_FALTANTE] program:{slug} sin objective asignado
  Propone: asignar objective via `program link-objective SLUG OBJECTIVE_ID`

[RELACION_FALTANTE] program:{slug} sin need asignado
  Propone: asignar need via `program link-need SLUG NEED_SLUG`

[CAMPO_FALTANTE] project:{slug} en DEV sin workspace_path
  Propone: asignar via `project update SLUG --workspace-path PATH`

[ESPERA_VENCIDA] espera #{id} ({tipo}) en program:{slug} — {dias} dias sin resolver
  Propone: resolver via `espera resolve ID` o investigar bloqueo

{si todo OK en D}
Estructura DB conforme.

---
Si no hay nada que actualizar:
KB al dia — no se encontraron inconsistencias.
```

Opciones del gate:

```yaml
question: "Que quieres hacer?"
header: "Auditoria KB"
options:
  - label: "Aplicar todo (A + B + C + D)"
    description: "Actualizar referencias, agregar avisos en estados, corregir formato y estructura"
  - label: "Solo referencias de comportamiento (A)"
    description: "Actualizar textos desactualizados en CLAUDE.md y aprendizaje"
  - label: "Solo avisos en estados activos (B)"
    description: "Reportar cambios relevantes para programs/projects en curso"
  - label: "Solo conformidad de datos (C)"
    description: "Completar content types faltantes, corregir acciones y perfiles"
  - label: "Solo conformidad estructural DB (D)"
    description: "Corregir relaciones faltantes, campos vacios, esperas vencidas"
  - label: "Solo archivos deprecados"
    description: "Renombrar archivos con nombre antiguo y actualizar referencias"
  - label: "Seleccionar uno por uno"
    description: "Reviso cada cambio propuesto antes de aplicar"
  - label: "Solo ver el reporte, sin aplicar nada"
    description: "Diagnostico sin modificar archivos"
```

Si no hay cambios en alguna categoria, omitir esa opcion del gate.

## FASE 5 — Aplicar

### Categoria A — Actualizar referencias de comportamiento

Para cada inconsistencia seleccionada:
```
Edit — reemplazar el texto desactualizado con el texto propuesto
```

### Categoria B — Reportar avisos de estado

Para cada aviso aprobado, agregar nota en el historial del program/project via CLI:

```bash
kb program add-historial SLUG --texto "⚠️ /actualiza [{estacion}]: {descripcion del cambio}"
# o para projects:
kb project add-historial SLUG --texto "⚠️ /actualiza [{estacion}]: {descripcion del cambio}"
```

### Refs deprecadas — Actualizar skills/agentes

Para cada skill/agente con referencias a archivos de estado filesystem:
1. Edit para reemplazar `.project-estado.md` → `project show SLUG --full`
2. Edit para reemplazar `.program-estado.md` → `program show SLUG --full`
3. Edit para reemplazar `index.md de programs → `program show SLUG --full`
4. Edit para reemplazar rutas `kb/producto/{modulo}/program-{slug}/` → CLI queries

Para cada referencia deprecada en otros archivos:
1. Edit para reemplazar `/{nombre-viejo}` → `/{nombre-nuevo}`

### Categoria C — Completar datos

- **Content type faltante en program:** Delegar a doc-writer para crear el tab correspondiente en el Google Doc del program (usar template `program-discovery` para obtener el scaffold del tab).

- **Perfil equipo incompleto:** Actualizar via CLI:
  ```bash
  kb person update EMAIL --rol "{rol}"
  ```

### Categoria D — Corregir estructura DB

Para cada RELACION_FALTANTE:
  - Ejecutar CLI para establecer relacion (ej: `program link-objective SLUG OBJECTIVE_ID`)

Para cada CAMPO_FALTANTE:
  - Ejecutar CLI para completar campo (ej: `project update SLUG --workspace-path PATH`)

Para cada ESPERA_VENCIDA:
  - Presentar al usuario para decision: resolver o mantener con nota

Para cada GATE_PENDIENTE:
  - Presentar al usuario para decision: aprobar, rechazar o mantener

### Reporte final

```
ACTUALIZACION COMPLETADA

A. Referencias de comportamiento: {N} docs modificados
B. Estado operativo:              {M} avisos registrados en historial
   - Refs deprecadas corregidas:  {R}
C. Conformidad de datos:          {K} entidades actualizadas
   - Content types creados:       {X}
   - Perfiles completados:        {Z}
D. Conformidad estructural DB:    {J} correcciones aplicadas
   - Relaciones establecidas:     {RE}
   - Campos completados:          {FC}
   - Esperas resueltas:           {ER}
```

Si se eligio "Solo ver el reporte": no ejecutar FASE 5, solo terminar con el reporte de FASE 4.

## Exclusiones absolutas (nunca tocar)

- `.claude/` — fuente de verdad del sistema (skills, agentes, settings). Excepto para corregir refs deprecadas detectadas en Cat B.
- `kb/archivos/` — binarios, PDFs, presentaciones
- repos clonados (fuera de la KB, ruta en `workspace_path` de mision en DB)
- `.app-manifest.json` — artefacto de build
- `.claude/agent-memory/*/MEMORY.md` — archivos legacy (migrados a `kb context`). Si existen, migrar via `kb context set` — no tratar como fuente de verdad.
- Programs/projects con estado completado en DB (historico inmutable)

## Tono

- Directo, eficiente. Espanol.
- Si no hay nada que actualizar: decirlo explicitamente ("KB al dia — no se encontraron inconsistencias.")
- No generar cambios triviales ni ruido — solo proponer edits con impacto real
- Gate siempre antes de escribir
- **Regla de opciones:** En cada punto de decision, presentar 2-4 opciones numeradas con recomendacion marcada + opcion abierta ("Otra cosa"). No hacer preguntas abiertas sin opciones (ver CLAUDE.md).
