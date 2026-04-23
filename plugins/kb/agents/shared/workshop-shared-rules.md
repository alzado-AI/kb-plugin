# Reglas compartidas de Workshops

Shared entre `/program` y `/project`. Parametro: `{ENTITY_TYPE}` = `program` o `project`.

## Busqueda de contexto previo

Al crear una entidad nueva, lanzar 4 busquedas en paralelo con graceful degradation:
- **KB local:** `kb search {keyword}` — en `/project` agregar `kb todo list --pending`
- **Google Workspace:** agente `external-searcher`
- **Project tracker:** buscar keyword en el provider activo (ver provider definition)
- **Internet:** `WebSearch(query="{feature} {modulo} {terminos de dominio}")` — saltar silenciosamente si falla o los resultados son genericos sin relacion al dominio

## Captura proactiva de errores

Cuando cualquier comando `kb` o de provider devuelva error (404, 500, 400, timeout):
1. Capturar inmediatamente — no esperar a que el usuario lo pida.
2. `kb todo create "BUG: kb {comando} devuelve {status_code}: {detalle}" --parent-type {ENTITY_TYPE} --parent-slug {SLUG}`.
3. Informar: "Detecte un error en `kb {comando}` — lo capture como tarea #{id}."
4. No asumir estado — si un query falla, el dato es desconocido, no negativo.

## Equipo por defecto

Al crear una entidad nueva, buscar el equipo del modulo via `kb person list --module {modulo}` + `kb team list`.

## Propagacion de completitud

Al finalizar, aplicar la regla de Propagacion de Completitud (ver CLAUDE.md): consultar `kb todo list --pending`, buscar acciones que matcheen el trabajo completado, y ofrecer completarlas via `kb todo complete ID`.

## Tono y estilo

- Directo, eficiente, colaborativo. Espanol chileno profesional.
- Nunca forzar un camino. El usuario siempre puede ir a cualquier estacion.
- Sintetizar antes de persistir.
- No bombardear con preguntas — una cosa a la vez.
- Pedir confirmacion cuando haya ambiguedad real, no por ritual.
