---
name: pipeline
domain: comercial
description: "Crear y gestionar pipelines de agentes automatizados. Modo conversacional: describe que quieres automatizar y el sistema crea el pipeline con los pasos y agentes correctos."
---

# /pipeline — Pipeline Builder

Crear y gestionar pipelines de agentes automatizados conversacionalmente.

## Modos

### Sin argumentos: listar pipelines
```bash
kb pipeline list --pretty
```
Muestra todos los pipelines existentes con sus steps.

### "ejecutar SLUG" o "run SLUG": trigger manual
Ejecutar un pipeline manualmente con contexto opcional.

```bash
# Sin contexto (usa defaults del pipeline)
kb pipeline run SLUG

# Con contexto que overridea defaults
kb pipeline run SLUG --context '{"periodo": "marzo 2026", "cliente": "Bravo Energy"}'
```

Si el usuario da instrucciones en lenguaje natural (ej: "ejecuta el reporte mensual para marzo"), interpretar el contexto y armar el JSON:
1. Buscar el pipeline por nombre o slug: `kb pipeline show SLUG`
2. Leer `default_context` para saber que variables acepta
3. Mapear las instrucciones del usuario a esas variables
4. Ejecutar `kb pipeline run SLUG --context '{...}'`

### Con descripcion: crear pipeline nuevo
El usuario describe lo que quiere automatizar en lenguaje natural. Tu trabajo es mapear eso a una cadena de agentes.

## Proceso de creacion

### 1. Entender el objetivo
Pregunta o infiere:
- Que evento dispara el pipeline? (feedback.created, meeting.created, etc.)
- Que pasos necesita? (triage, issue, code, review, deploy, etc.)
- Donde necesita aprobacion humana?

### 2. Mapear a agentes disponibles

Consulta los agentes disponibles:
```bash
kb agent list --pretty
```

Mapeo de roles a agentes: ver `pipeline-builder` §Agentes disponibles (clasificacion canonica por categoria: Radar, Refinador, Core Developer, PM Project, Explorador, Arquitecto, Ops). El catalogo live esta en `kb agent list --pretty`.

**IMPORTANTE — 2 tipos de pipelines de codigo:**

1. **Fix/mejora de la plataforma** (core): usa `core-developer` → clona el repo de la plataforma, implementa, push, PR. El humano mergea en GitHub.

2. **Feature para un cliente** (PM project): usa `app-builder` → workspace aislado en ~/pm-apps/, prototipo local. No toca el repo de la plataforma.

Pregunta al usuario cuál es su caso si no queda claro.

### 3. Mostrar preview

Presenta al usuario la cadena propuesta:

```
Pipeline: feedback-to-deploy
Trigger:  feedback.created

  ⚡  1. Triage feedback (feedback-triager) [APPROVAL]
  →   2. Create dev-ready issue (issue-writer) [APPROVAL]
  →   3. Implement fix (code-implementer)
  →   4. Review code (code-reviewer) [APPROVAL]
  →   5. Create PR and deploy (code-publisher)
```

Preguntas clave via AskUserQuestion:
- Esta bien esta cadena? Quieres agregar/quitar pasos?
- Que pasos necesitan tu aprobacion? (recomendacion: triage, plan de implementacion, deploy)
- Quieres ajustar algun prompt?

### 4. Ejecutar creacion

Una vez confirmado, ejecuta:

```bash
# Crear pipeline
kb pipeline create {slug} --name "{name}" --trigger-event {event} --description "{desc}"

# Agregar pasos de actividad
kb pipeline add-step {slug} --node-type activity --activity {activity-slug} \
  --name "{step_name}" --order {N} \
  [--inputs '{"key":"{{trigger.x}}"}'] [--depends-on 1,2]

# Agregar un gate de aprobacion (control node — solo en execution_class=orchestration)
kb pipeline add-step {slug} --node-type control --control-type gate_approval \
  --name "{step_name}" --order {N} \
  --control-config '{"title_template":"{title}"}'

# Activar
kb pipeline activate {slug}
```

### 5. Confirmar

Mostrar:
```bash
kb pipeline show {slug}
```

Y decir: "Pipeline creado y activo. Cuando ocurra un evento '{event}', se disparara automaticamente."

## Eventos disponibles

| Evento | Descripcion | Fuente |
|--------|------------|--------|
| feedback.created | Nuevo feedback sobre la plataforma KB | Satellite sync o directo |
| task.resolve_requested | Se pide resolucion autonoma de una tarea via POST | Tasks API |
| meeting.created | Nueva reunion registrada | Calendar sync |
| approval.approved | Aprobacion del CPO | Dashboard |
| approval.rejected | Rechazo del CPO | Dashboard |
| issue.moved_to_backlog | Issue movido a Backlog | Linear sync |
| email.received | Nuevo email en el inbox | Gmail poller |

## Gestion de pipelines existentes

```bash
# Ver pipeline con steps
kb pipeline show {slug}

# Pausar (deja de aceptar nuevos triggers)
kb pipeline pause {slug}

# Reactivar
kb pipeline activate {slug}

# Ver ejecuciones
kb pipeline runs --pipeline {slug}

# Agregar paso de actividad (idempotente: si ya existe con ese --order, lo actualiza)
kb pipeline add-step {slug} --node-type activity --activity {activity-slug} --name "{name}" --order {N}

# Editar paso existente sin borrar/recrear
kb pipeline update-step {slug} --order {N} [--activity nuevo-activity] [--name "Nuevo"] [--inputs '{"..."}' ] [--depends-on 1,2]

# Quitar paso (el DAG se re-cablea: dependientes heredan parents del step eliminado)
kb pipeline remove-step {slug} --order {N}
```

## Ejemplos de pipelines comunes

### Feedback a Deploy — Core (fix de la plataforma)
feedback.created → feedback-triager [approval] → issue-writer → issue-analyzer [approval] → core-developer → code-reviewer [approval]

5 pasos, 3 approvals. El core-developer clona el repo, implementa, commitea, pushea, crea PR. El humano mergea en GitHub.

### Feedback a Prototipo — PM Project (feature para cliente)
feedback.created → feedback-triager [approval] → doc-writer [approval] → app-builder → prototype-tester [approval]

6 pasos, 3 approvals. El app-builder trabaja en workspace aislado ~/pm-apps/{slug}/. No toca el repo de la plataforma.

### Meeting a Actions (Ops)
meeting.created → calendar-discoverer → meeting-parser [approval] → meeting-persister

### Daily Health (Ops)
interval 86400 → kb-healer (1 step, sin approval)

### Weekly Strategy Review
cron "0 9 * * 1" → estrategia-reader (1 step, sin approval)

### Manual Report (trigger manual con contexto)
manual + default_context `{"periodo": "ultimo mes"}` → erp-reporter (1 step)
El usuario da play desde la UI o via `/pipeline ejecutar report-monthly periodo=marzo 2026`
