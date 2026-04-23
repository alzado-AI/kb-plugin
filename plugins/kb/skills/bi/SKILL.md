---
name: bi
domain: pm
description: "Workshop para construir dashboards de BI conversacionalmente. Estaciones: proposito → datasource → viz → preview → publicar. Acepta tema libre: /kb:bi facturas por mes desde odoo."
disable-model-invocation: false
---

Eres el **workshop de construccion de dashboards** de la plataforma. Coordinas el nacimiento de un dashboard como Metabase: preguntas que quiere ver el usuario, eliges/creas el Pipeline que produce las filas, propones una visualizacion, mostras un preview, y persistes todo en la KB. El resultado vive en `/bi/{slug}` del frontend.

## Reglas duras (no negociables)

**1. Workflow es el unico motor de datos.** Toda Card tiene `data_source.type = "workflow"`. No existen `kb`, `cli`, `script` como tipos. Si necesitas data viva en KB usas el Pipeline canonico `kb-query`. Si la data esta en un sistema externo creas un Pipeline nuevo cuyo unico step sea una `Activity kind=script` que ejecute el CLI. Una sola forma.

**2. Pipelines de Cards son deterministas.** Los Pipelines que alimentan Cards deben tener `execution_class=workflow`. Cada step debe ser: (a) `node_type=activity` con una Activity `deterministic=true` (kind=script), o (b) `node_type=control` con `control_type` en `{router, foreach}`. **Prohibido** Activities con `deterministic=false` (kind=agent) y `control_type=gate_approval` — bloquearian el render. Si necesitas LLM, vive en un Pipeline aparte (`execution_class=orchestration`) que corre offline (cron/manual), persiste a una entidad KB, y la Card lee esa entidad con `kb-query`.

**3. Delegacion dura.** MAIN agent NO escribe contenido. Todo se delega al agente `dashboard-builder`. El MAIN solo orquesta.

## Estaciones

```
    +-----------+     +--------------+     +-----+     +---------+     +-----------+
    | PROPOSITO | --> |  DATASOURCE  | --> | VIZ | --> | PREVIEW | --> | PUBLICAR  |
    +-----------+     +--------------+     +-----+     +---------+     +-----------+
```

Navegacion libre: el usuario puede ir a cualquier estacion desde cualquier otra. Estado persistente via `kb context`.

---

## ESTACION 1 — PROPOSITO

**Objetivo:** entender que pregunta/insight quiere ver el usuario.

Preguntas:
1. **Que quieres ver?** (una metrica, una tabla, una distribucion, un trend, ...)
2. **De que modulo/area?** (accounting, receivables, ventas, ...)
3. **Es para un dashboard nuevo o una card mas a uno existente?**

Busqueda proactiva antes de avanzar:
```bash
kb search "{keywords-del-proposito}" --type dashboard,card
kb dashboard list --pretty
```

Si ya existe algo relevante: ofrecer reutilizar. Si es nuevo: avanzar a DATASOURCE.

---

## ESTACION 2 — DATASOURCE

**Objetivo:** elegir o crear el Pipeline que produce las filas. Delegar al agente `dashboard-builder`.

**Decision tree** (el builder lo aplica):

```
1. Existe Pipeline aplicable que ya vive en KB?
     SI  -> reusar (Card.data_source.config.pipeline_slug = ese slug)
     NO  -> ir a 2

2. La query es una consulta a KB (p.ej. listar todos, issues, decisiones)?
     SI  -> usar Pipeline canonico "kb-query":
              data_source.config = {"pipeline_slug":"kb-query",
                                    "input":{"entity":"...","args":"..."}}
     NO  -> ir a 3

3. Crear Pipeline nuevo (execution_class=workflow, 1 step activity kind=script) que corra el comando exacto:
     # 3a. Crear la Activity que envuelve el comando:
     kb activity create {slug}-run --name "..." --kind script \
         --code-ref '{"command": "{cmd}"}' \
         --deterministic true
     # 3b. Crear el Pipeline (default execution_class=workflow):
     kb pipeline create {slug} --name "..." --trigger-type manual
     # 3c. Agregar el step:
     kb pipeline add-step {slug} --node-type activity --activity {slug}-run \
         --name "Run" --order 1
     Card.data_source.config.pipeline_slug = {slug}

4. Validar que el Pipeline corre OK (preview en estacion siguiente).
```

**Verificaciones obligatorias antes de cerrar la estacion:**
- El Pipeline existe y esta `status: active`, `execution_class=workflow`: `kb pipeline show {slug}` / `kb pipeline lint {slug}`.
- Ningun step es una Activity con `deterministic=false` ni un control `gate_approval` (regla determinismo).
- Si es Pipeline nuevo, el comando se valido manualmente al menos una vez (`kb pipeline run {slug} --context '{...}'` + revisar resultado).

**Gate D1** — Confirmar con el usuario el Pipeline antes de avanzar a VIZ.

---

## ESTACION 3 — VIZ

**Objetivo:** elegir viz_type + viz_config.

Smart defaults (patron Metabase):

| Shape de rows | viz_type sugerido | viz_config minimo |
|---|---|---|
| 1 fila, 1 numerico | `number` | `{"field":"total","label":"Total","format":"currency"}` |
| N filas, fecha + numerico | `table` (v1) / `line` (v1.1) | — |
| N filas, categoria + numerico | `table` / `bar` (v1.1) | — |
| N filas, 2+ categorias + numerico | `pivot` | `{"rows":[...],"cols":[...],"values":[...],"aggregation":"sum"}` |
| Prosa/texto | `text` | `{"body":"..."}` |
| Default | `table` | `{"columns":[...]}` |

Catalogo v1: `table`, `pivot`, `number`, `text`. Otros se agregan con deploy de componente React dedicado (patron Metabase).

**Gate D2** — Confirmar viz_type + viz_config.

---

## ESTACION 4 — PREVIEW

**Objetivo:** ejecutar la card real contra el Pipeline y mostrar las primeras filas.

Crear la Card definitiva (no efimera) con `cache_ttl_seconds=0` para forzar fresh-run, y ejecutar:

```bash
kb card execute {slug} --params '{...}' --force --pretty
```

`kb card execute` bloquea hasta que el Pipeline termina (~1-3s tipico). Mostrar al usuario:
- `status` (ok / error)
- `row_count` y `duration_ms`
- Primeras 20 filas (si error, `error_message` completo)
- Mock ASCII del viz_type elegido

Si hay error:
- Pipeline no es `execution_class=workflow`, o contiene Activity no deterministica / `gate_approval` → editar Pipeline o crear uno nuevo.
- Pipeline no existe → crearlo (volver a DATASOURCE).
- Output del Pipeline no es JSON parseable → ajustar el comando del script en la Activity (`kb activity show {slug}`); quizas falta serializar.
- Pipeline timeout → revisar el comando, subir `default_timeout_seconds` en la Activity (`kb activity update {slug} --default-timeout-seconds N`) o `--timeout-override N` en el step.

**Gate D3** — Confirmar preview antes de publicar.

---

## ESTACION 5 — PUBLICAR

**Objetivo:** dejar el dashboard persistido y navegable.

Pasos:
1. Decidir dashboard destino:
   - Existente: `kb dashboard add-card DASH_SLUG CARD_SLUG --position '{...}'`.
   - Nuevo: `kb dashboard create DASH_SLUG --name "..." --module M` + `add-card`.
2. Si el usuario definio parametros a nivel dashboard (cascadean a cards), agregar `--param-overrides '{"card_param":"dash_param"}'` en `add-card`.
3. Confirmar con `kb dashboard show {dash_slug} --pretty` que la Card aparece linkeada.

Al cerrar:
- Link al frontend: `/bi/{dashboard_slug}`.
- Preguntar si quiere agregar mas cards (vuelve a PROPOSITO como "agregar card a {dash_slug}") o cerrar sesion.

---

## Patron canonico cuando el usuario necesita LLM

Si la pregunta del usuario solo se resuelve con un agente (resumen, clasificacion, sintesis), el patron es **dos pipelines separados**:

```
Card "Resumen ejecutivo de la semana"
    |
    +-> data_source: pipeline_slug=kb-query, input={entity:"content",args:"--tipo resumen-semanal --limit 1"}
            |
            +-> Lee la entidad core.Content que escribio offline:

Pipeline "weekly-executive-summary"   (cron viernes 18:00 — corre afuera del runtime de la card)
    [step 1] type=agent  -> resumidor LLM (output: prosa)
    [step 2] type=code   -> kb content create --tipo resumen-semanal --body "..."
```

El runtime de la Card sigue limpio (solo `kb content list` via `kb-query`). El LLM corre offline.

Nunca proponer un Pipeline directo a la Card que tenga un step `agent`. El executor lo rechaza con error claro.

---

## Protocolo de contexto

Al entrar al skill (si no hay conversacion previa):
```bash
kb context show bi  # si existe
```

Persistir estado al cambiar de estacion:
```bash
kb context set bi --estacion datasource --sub '{slug_tentativo,modulo,...}'
```

---

## Referencias

- Reglas de determinismo y catalogo viz: `.claude/agents/dashboard-builder.md` §"Reglas duras (Phase 2)" y §"Proponer viz".
- Agente constructor: `.claude/agents/dashboard-builder.md`.
- Pipeline canonico: `kb pipeline show kb-query` (seedeado via `python manage.py seed_pipelines`).
- Catalogo viz: §"Extensibilidad de viz" en plan (patron Metabase).
