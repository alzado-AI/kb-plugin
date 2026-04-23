---
name: trabajar
domain: core
description: "Scanner de trabajo: escanea TODAS las fuentes (KB, Gmail, Chat, Drive, Linear, Calendar), detecta donde el PM es bottleneck, y presenta tareas priorizadas por impacto. Auto-detecta progreso entre sesiones. Sin argumentos: scan completo. Con modulo: /kb:trabajar accounting."
disable-model-invocation: false
---

El PM quiere un scan completo de trabajo — lee TODAS las fuentes, detecta donde es bottleneck, y presenta tareas priorizadas por impacto.

## Drift findings como tareas implicitas

Antes de delegar al trabajo-scanner, consultar el detector de drift del dominio:

```bash
KB_CLI="kb"
"$KB_CLI" drift list --severity warn --pretty 2>/dev/null
"$KB_CLI" drift list --severity error --pretty 2>/dev/null
"$KB_CLI" conflict list --pending --pretty 2>/dev/null
```

Cada `DriftFinding` con `status=open` es una tarea implicita que el PM deberia atender (un producto sin mapping, un cliente sin tipo, una sociedad mencionada que no existe como LegalEntity). Incluirlas en el output del scan **bajo su propia seccion** "Salud del dominio (white-label)" — separadas de las tareas normales para que sea claro que son del subsistema de configuracion, no de la operacion diaria.

Cada `Conflict` con `status=pending` tambien es una tarea implicita: alguien propuso cambiar un valor del dominio y necesita resolucion explicita.

## Paso 1: Obtener datos

Lanza el agente `trabajo-scanner` (Agent tool, subagent_type="trabajo-scanner") en foreground con este prompt:

```
Scanner de trabajo del PM. Fecha actual: {fecha de hoy}.
{Si $ARGUMENTS tiene contenido: "Filtro por modulo: $ARGUMENTS. Muestra solo tareas de ese modulo."}
{Si $ARGUMENTS esta vacio: "Sin filtro. Scan completo de todas las fuentes."}
```

**IMPORTANTE:**
- El agente persiste estado en DB via `kb context set trabajo-estado` (NO crea archivos)
- Todos los MCP calls los hace el agente internamente
- Foreground siempre (necesita permisos MCP interactivos)

El agente devuelve datos estructurados (secciones `=== META ===`, `=== BOTTLENECK ===`, etc.), NO output formateado.

## Paso 2: Formatear output

Tomar los datos del agente y renderizarlos con este template. Usar un contador secuencial `#` que avanza cross-seccion.

```
# Trabajar — {fecha de hoy}

{Si hay seccion PROGRESO:}
## Progreso desde ultima sesion
{para cada item: "- {descripcion}"}

{Si hay seccion BOTTLENECK:}
## Bloqueando a otros (Prioridad Alta)
| # | Que hacer | Quien espera | Desde | Skill |
|---|-----------|--------------|-------|-------|
| {seq} | {que} | {quien_espera} | {desde} | {skill} |

{Si hay seccion COMPROMISOS:}
## Compromisos pendientes (Prioridad Alta)
| # | Compromiso | A quien | Cuando | Skill |
|---|------------|---------|--------|-------|
| {seq} | {compromiso} | {a_quien} | {cuando} | {skill} |

{Si hay seccion NOTIFICACIONES:}
## Avisar stakeholders
| # | Avisar a | Sobre que | Completado | Skill |
|---|----------|-----------|------------|-------|
| {seq} | {avisar_a} | {sobre} | {completado} | {skill} |

{Si hay seccion INBOX:}
## Inbox
| # | Que | De donde |
|---|-----|----------|
| {seq} | {que} | {fuente} |

{Si hay seccion EQUIPO:}
## El equipo
| Persona | Trabajando en | Estado | Necesita de ti? |
|---------|---------------|--------|-----------------|
| {persona} ({rol}) | {trabajando_en} | {estado} | {necesita_de_ti} |
{Si hay wip_alerta:}
**WIP:** {persona} tiene {N} projects en {team} — overcommit

{Si hay seccion STALENESS:}
## Se enfria (Prioridad Media)
| # | Que | Dias sin mover | Skill |
|---|-----|----------------|-------|
| {seq} | {que} | {dias}d | {skill} |

{Si hay seccion OPORTUNIDAD:}
## Oportunidad sin explorar
| # | Program | RICE | Skill |
|---|---------|------|-------|
| {seq} | {program} | {rice} | {skill} |

{Si hay seccion PIPELINE:}
## Pipeline

### Stock Oportunidades (issues)
{por team:}
#### {team}

**To Do** ({N})
| Issue | Titulo | Prioridad | Assignee |
|-------|--------|-----------|----------|
| {id}  | {titulo} | {P}     | {nombre} |

**Backlog** ({N})
| Issue | Titulo | Prioridad | Assignee |
|-------|--------|-----------|----------|
| {id}  | {titulo} | {P}     | {nombre} |

**Triage** ({N})
| Issue | Titulo | Prioridad | Assignee |
|-------|--------|-----------|----------|
| {id}  | {titulo} | {P}     | {nombre} |

{Si todo < 5:} **Stock bajo ({N}/5) — necesita {5-N} mas en To Do**
Sugerencias (min 10):
| # | Candidato | Origen | Estado | Skill |
|---|-----------|--------|--------|-------|
| {seq} | {titulo/descripcion} | {Triage/Backlog/KB} | {completo/falta info} | {skill} |

### Stock Projects (projects)
{por team:}
#### {team}

**Build** ({N})
| Project | Titulo | Lead |
|---------|--------|------|
| {id}    | {titulo} | {nombre} |

**Issue breakdown** ({N})
| Project | Titulo | Lead |
|---------|--------|------|
| {id}    | {titulo} | {nombre} |

**Discovery** ({N})
| Project | Titulo | Lead |
|---------|--------|------|
| {id}    | {titulo} | {nombre} |

**Idea** ({N})
| Project | Titulo | Lead |
|---------|--------|------|
| {id}    | {titulo} | {nombre} |

{Si discovery < 2:} **Stock bajo ({N}/2) — avanzar discovery**
Sugerencias (min 5):
| # | Project | Program | RICE | Objective | Skill |
|---|---------|---------|------|-----------|-------|
| {seq} | {project} | {program} | {rice} | {objective} | {skill} |

{Si hay seccion LANDSCAPE:}
## Landscape estrategico
{para cada item: "- {senal} → {skill}"}
{Si hay sin_ancla:}
**Sin ancla:** {N} acciones sin modulo, {N} projects sin objective → `/kb:estrategia review`

{Si hay seccion REUNIONES:}
## Reuniones proximas
| Cuando | Reunion | Estado | Skill |
|--------|---------|--------|-------|
| {cuando} | {reunion} | {estado} | {skill} |

{Si hay seccion QUICK WINS:}
## Quick wins
{para cada item: "- {que} → {skill}"}

---
Fuentes: {ok} {si fallidas != "ninguna": "({fallidas})"}

/kb:pendientes | /kb:estrategia | /kb:matriz
```

Reglas de formateo:
- Numeros `#` secuenciales cross-seccion (1, 2, 3... sin reiniciar entre secciones)
- Omitir secciones enteras si el agente no las devolvio
- **Formato identico por team** — en PIPELINE, cada team debe tener exactamente las mismas tablas (Stock Oportunidades + Stock Projects), mismos thresholds y misma estructura de sugerencias. Si un team tiene datos y otro no, mostrar "Sin datos" en vez de omitir la seccion del team.
- Tono profesional: informativo y directo
- Si el agente devuelve secciones inesperadas o formato raro, mostrar el output raw del agente como fallback

## Paso 3: Presentar opciones interactivas

Despues de renderizar el reporte, tomar la seccion AGENDA SUGERIDA del agente (top 5 items priorizados por impacto) y presentarlos como `AskUserQuestion`:

```yaml
question: "En que quieres trabajar ahora?"
options:
  - label: "{descripcion del item 1}" (Recommended)
    description: "{skill a ejecutar}"
  - label: "{descripcion del item 2}"
    description: "{skill a ejecutar}"
  - label: "{descripcion del item 3}"
    description: "{skill a ejecutar}"
  - label: "{descripcion del item 4}"
    description: "{skill a ejecutar}"
  - label: "{descripcion del item 5}"
    description: "{skill a ejecutar}"
```

Cada opcion debe incluir:
- Label descriptivo con contexto (ej: "Desbloquear a {persona}: {descripcion}", "Atender compromiso: {descripcion}", "Reactivar: {descripcion}", "Preparar reunion: {nombre}", "Explorar oportunidad: {program}")
- La primera opcion lleva "(Recommended)" — es la de mayor impacto
- El skill concreto a ejecutar en description

Si el usuario elige una opcion, ejecutar el skill correspondiente directamente.
