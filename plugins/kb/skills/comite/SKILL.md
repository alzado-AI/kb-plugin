---
name: comite
domain: pm
description: "Comite de triage: revisar issues en Triage, investigar antecedentes, decidir destino (Backlog, cancelar, program/project, consolidar), detectar gaps KB sin Linear. Sin args: scan completo. Con team: /kb:comite receivables. Con issue: /kb:comite AR-1910."
disable-model-invocation: false
---

Eres el **workflow de triage de producto**. Tu rol es revisar issues en estado **Triage** en Linear, investigar antecedentes para tomar decisiones informadas, y decidir el destino de cada issue. NO escribes specs dev-ready — eso es responsabilidad de `/kb:refinar`.

**Reglas de routing del dominio.** Antes de decidir destino, consultar reglas de triage activas: `kb rule resolve --contexto '{"tipo":"triage"}'`. Si una regla activa indica destino especifico para cierto patron de issue, respetarla y citar `[rule:slug]` en la decision. Carga tambien `kb org-context --module {modulo} --format prompt` para detectar si el issue toca un area del dominio donde ya existen programs/projects — evitar duplicar trabajo.

**Contexto metodologico:** Leer el template oficial: cache local `~/.kb-cache/u/{user_id}/templates/issue-body.md` o fallback `kb template show issue-body`. Leer `kb context show metodologia` si existe para entender estados y flujos.

**Contexto taxonomico:**
- Vista Oportunidades en el project-tracker = issues sin proyecto (Triage → Backlog → To do)
- Este skill opera **solo sobre Triage**. Backlog se trabaja con `/kb:refinar`.
- Label relevante unico: `batman -> launchpad` (si viene de soporte)

**Providers:** Ver `.claude/agents/shared/provider-resolution.md`. Capabilities: project-tracker.

**Flujo general:**
```
Triage → /kb:comite (decide destino) → Backlog → /kb:refinar (dev-ready) → To do → /kb:batman (fix rapido)
```

## MODELO DE NAVEGACION: ESTACIONES

```
+--------+     +----------+     +----------+
| CARGA  |---->| DECISION |---->| APLICAR  |
+--------+     +----------+     +----------+
(inventario     (por issue:     (update
 Triage,         evidence card    Linear +
 investigar,     + recomendacion, KB batch)
 detectar        destino)
 gaps KB)
```

**Regla:** Las estaciones son secuenciales por defecto pero el usuario puede saltar a cualquiera o pedir solo una.

## ENTRADA Y ROUTING

Routing estandar de pipeline (ver `.claude/agents/shared/routing-guide.md` §"Patron de Routing de Skills de Pipeline"). En modo single-issue, salta a DECISION directo (con investigacion previa).

---

## ESTACION: CARGA

### Proposito
Obtener issues en Triage de Linear, investigar cada uno, detectar gaps KB, y preparar evidence cards para decision.

### Ejecucion

**Paso 1: Traer oportunidades en Triage**

Obtener issues en Triage via el project-tracker provider activo (ver provider definition para comando de listado de oportunidades/issues por status).

Si no hay issues en Triage, informar y ofrecer opciones (ver Backlog con `/kb:refinar`, o detectar solo GAPS).

**Paso 2: Agrupar y presentar**

Agrupar por team. Presentar como dashboard:

```
# Comite de Triage — {fecha}

## {Team} ({N} issues en Triage)

| Issue | Tema | Problema | Labels |
|--------|------|----------|--------|
```

**Paso 3: Detectar clusters**

Agrupar issues con temas similares (keywords comunes en titulo/descripcion, mismo cliente, relaciones existentes). Marcar clusters en la tabla.

**Paso 4: Investigar en paralelo**

Para cada issue (o cluster), investigar en paralelo (TODOS en foreground):

a) **Issue completo (project-tracker):**
Leer detalle del issue via el project-tracker provider activo (ver provider definition para comando de show/detalle de issue).
Extraer: titulo, descripcion, comments, relations, labels, assignee.

b) **KB local:**
```bash
kb search "{keywords}" --limit 10
kb issue find "{keywords}"
```

c) **Voice of Customer** (1 vez por modulo — reutilizar si ya se corrio):

Si ya se invoco VoC para este modulo en esta sesion de comite, reutilizar el resultado anterior sin relanzar. Solo lanzar si es la primera vez para el modulo:
```
Agent(subagent_type="voice-of-customer",
  prompt="Modulo: {modulo}. Keywords: {keywords del titulo}. Days back: 90.")
```

d) **Google Workspace:**
```
Agent(subagent_type="external-searcher",
  prompt="Buscar en Gmail y Chat: {keywords del titulo}. Max 10 resultados.")
```

**Paso 5: Sintetizar briefs de decision**

Por cada issue, producir un **brief de decision** (NO un spec dev-ready):

```
## {IDENTIFIER}: {titulo}

### Lo que dice Linear
{descripcion + comments clave}

### Evidencia encontrada
- KB: {tickets/tasks/meetings relacionados}
- VoC: {pain points, clientes afectados, frecuencia}
- GWS: {emails/chats relevantes}

### Evaluacion
- Evidencia: {alta|media|baja}
- Clientes afectados: {N}
- Duplicados potenciales: {si hay}

### Recomendacion
{destino sugerido con justificacion breve}
```

**Paso 6: Acumular para importacion batch**

NO importar a KB aqui. Acumular los briefs de decision para importar en batch en la estacion APLICAR (1 sola invocacion de issue-writer en vez de N).

**Paso 7: Detectar GAPS**

Buscar items en KB que no tienen representacion en Linear (trabajo oculto):

```bash
kb issue list --module {modulo}
kb todo list --pending
kb question list --pending
```

Cruzar con el project-tracker provider: identificar tickets/tasks/decisions KB que NO tienen `external_id` (no estan en el tracker externo). Presentar como:

```
## Gaps: Trabajo en KB sin tracker externo ({N} items)

| # | Tipo | Titulo | Modulo | Creado | Accion sugerida |
|---|------|--------|--------|--------|----------------|
```

**Paso 8: Preguntar como proceder**

Usar `AskUserQuestion` con opciones:
- Decidir destino de todos (Recommended)
- Decidir solo {team}
- Decidir cluster "{nombre}"
- Crear issues en tracker para gaps KB
- Issue especifico

---

## ESTACION: DECISION

### Proposito
Para cada issue en Triage, mostrar evidence card y decidir destino.

### Ejecucion

Iterar por cada issue. Mostrar brief de decision (de CARGA) y ofrecer decision via `AskUserQuestion`:

**Pregunta:** "{IDENTIFIER}: {titulo} — que hacemos?"

**Opciones** (dinamicas segun contexto):
- **Mover a Backlog** (Recommended si evidencia media) — Necesita refinamiento con `/kb:refinar`
- **Cancelar** — No aplica o no vale la pena
- **Convertir a program/project** — Si es >5 dias o necesita discovery
- **Consolidar con {ID}** — Si se detecto duplicado
- **Necesita comite** — Flag para discutir en reunion
- **Mantener en Triage** — Necesita mas contexto antes de decidir

Si elige "Convertir a program/project": sugerir derivar a `/kb:program` o `/kb:project` segun complejidad.

Si elige "Consolidar": identificar issue principal, marcar otros como duplicados.

**Prioridad:** Si el issue esta en `sin-prioridad`, preguntar si quiere asignar prioridad ahora. No forzar.

**Para GAPS KB:** Ofrecer crear issue en el project-tracker para items huerfanos.

Registrar todas las decisiones para aplicar en batch.

**IMPORTANTE — Consolidacion de duplicados en el project-tracker:**
El project-tracker puede cancelar automaticamente los issues marcados como duplicados (ver provider definition para comando de relacion de duplicado). Por lo tanto, ANTES de crear la relacion de duplicado:
1. Actualizar el issue principal con toda la evidencia de los issues que se van a cancelar
2. La descripcion DEBE empezar con callout: `> **Issue consolidado** — incorpora contexto de {IDs cancelados}, ambos marcados como duplicados de este.`
3. Cada cliente/reporte de los issues cancelados debe quedar identificado con su issue original: `**{Cliente}** ({fecha}, ex {ID}): {detalle}`
4. Solo despues de que el issue principal es autocontenido, crear las relaciones de duplicado

---

## ESTACION: APLICAR

### Proposito
Reflejar todas las decisiones en Linear y KB en batch.

### Ejecucion

**Paso 1: Resumen**

```
## Resumen de Decisiones

| # | Issue | Decision | Detalle |
|---|-------|----------|---------|
| 1 | AR-1910 | Consolidar | Duplicado de AR-1642, AR-1845 |
| 2 | AR-1936 | Mover a Backlog | Feature request, churn signal |
```

**Paso 2: Confirmar**

`AskUserQuestion`:
- Aplicar todas (Recommended)
- Revisar una por una
- Cancelar

**Paso 3: Ejecutar**

Para cada decision:
- **Mover a Backlog:** Actualizar status del issue a "Backlog" via el project-tracker provider activo (ver provider definition)
- **Cancelar:** Actualizar status del issue a "Canceled" via el project-tracker provider activo
- **Consolidar:** PRIMERO actualizar issue principal en KB con callout + evidencia via `issue-writer` modo CONSOLIDAR, LUEGO sincronizar al project-tracker: actualizar descripcion del issue principal, FINALMENTE crear relacion de duplicado via el project-tracker provider (el tracker cancela automaticamente el source)
- **Actualizar KB:** `kb issue update {ID} -e {estado} [-p {prioridad}]`
- **Importar a KB (batch):** Delegar UNA sola invocacion de `issue-writer` con todos los issues:
  ```
  Agent(subagent_type="issue-writer",
    prompt="IMPORTAR BATCH de tickets de Linear.
    Tickets: [{identifier, titulo, descripcion, contexto_investigacion, modulo, decision} ...]")
  ```

**Paso 4: Persistir resultado**

Persistir directamente via KB CLI:
```bash
kb learning create "Resultado comite de triage {fecha}: Tickets en Triage revisados: {N}. Decisiones: {resumen}. Gaps KB detectados: {N}. Issues creados para gaps: {N}." --tipo proceso
```

**Paso 5: Sugerencia de siguiente paso**

Presentar:
```
{N} issues movidos a Backlog. Quieres refinar alguno? (`/kb:refinar {ID}`)
```

**Paso 6: Propagacion de completitud**

```bash
kb todo list --pending
```

Buscar acciones tipo "revisar oportunidades", "comite", "triage" y ofrecer completar.
