---
name: investiga
domain: pm
description: "Investigar empresas, competidores o soluciones de mercado desde la perspectiva de Product Management. Analisis competitivo, benchmarking de features, landscape de mercado, pricing, posicionamiento."
disable-model-invocation: false
---

el usuario quiere investigar un competidor, producto o solucion de mercado.

## Paso 1: Obtener datos

Usa el agente `product-teardown` (Agent tool, subagent_type="product-teardown") para realizar la investigacion.

Si el usuario incluyo el tema junto al comando (ej: `/kb:investiga Xero conciliacion bancaria`, `/kb:investiga competidores contabilidad Latam`), lanza el agente directamente con $ARGUMENTS como tema de investigacion.

Si no incluyo detalle, pregunta brevemente que quiere investigar.

El agente devuelve datos estructurados (secciones `=== META ===`, `=== MODULOS ===`, etc.), NO output formateado.

## Paso 2: Formatear output

Tomar los datos del agente y renderizarlos con este template:

```
{Si hay seccion === ADVERTENCIA === en el output del agente, renderizar PRIMERO como blockquote grande:}
> ⚠️ **Advertencia**: {texto de ADVERTENCIA}

# Teardown: {producto de META}
**Empresa:** {empresa} | **Mercado:** {mercado}
**Propuesta de valor:** {propuesta_valor}
**Pricing:** {pricing} | **Plataformas:** {plataformas}

---

(para cada bloque modulo: en MODULOS:)
## {modulo}
**Problema que resuelve:** {problema}

### Features
{para cada feature: "- **{name}**: {description}"}

### Flujo de usuario
{flujo, numerado}

### Integraciones
{integraciones}

{Si limitaciones != "sin info": "### Limitaciones\n{limitaciones}"}

---

## Capacidades Tecnicas
{para cada item en CAPACIDADES TECNICAS: "- **{tipo}**: {detalle}"}

## Diferenciadores
{para cada item en DIFERENCIADORES: "- {item}"}

## Gaps y Limitaciones
{para cada item en GAPS: "- {item}"}

{Si hay seccion COMPARATIVA:}
## Comparativa
| Feature | {producto1} | {producto2} |
|---------|-------------|-------------|
{para cada item: "| {feature} | {valor1} | {valor2} |"}

## Fuentes consultadas
{Si === FUENTES === tiene URLs: para cada linea "url: U | tipo: T | nota: N" renderizar "- [{U}]({U}) — {T}: {N}"}
{Si no hay URLs: "_El agente no cito fuentes externas._"}
**Confianza global**: {confianza_global de FUENTES}
```

Reglas de formateo:
- Omitir secciones vacias **excepto `## Fuentes consultadas` y `=== ADVERTENCIA ===`** — esas siempre se muestran (vacias, son la senal al usuario).
- Si el agente devuelve secciones inesperadas o formato raro, mostrar el output raw del agente como fallback.

## Paso 3: Post-resultado

**Guardrail de fuentes — bloqueo duro.** Antes de ofrecer persistir, parsear `=== FUENTES ===` del output crudo del agente y extraer la lista de URLs.

**Caso A — hay al menos 1 URL** (o `confianza_global` ∈ {alta, media, baja}):

Pregunta a el usuario si quiere persistir el resultado como learning de referente. Si dice que si, ejecutar:

```
"$KB_CLI" learning create "{empresa}" --tipo referente --body "{body_completo_renderizado}" \
  --source "{url_principal}" \
  --sources "{urls_separadas_por_coma}"
```

- `{url_principal}` = la URL con `tipo: oficial` si existe; si no, la primera URL listada.
- `{urls_separadas_por_coma}` = TODAS las URLs de `=== FUENTES ===`, en el orden en que aparecen, unidas con `,` (sin espacios).
- Si el usuario quiere persistir datos accionables en vez de learning, usar `"$KB_CLI" todo create` o `"$KB_CLI" question create` segun corresponda.

**Caso B — `=== FUENTES ===` vacio o `confianza_global: sin_fuentes` o presencia de `=== ADVERTENCIA ===`**:

NO llamar `"$KB_CLI" learning create`. Mostrar al usuario:

> El agente no cito fuentes externas. No se puede persistir este teardown como learning porque no hay evidencia verificable — un learning sin fuentes es indistinguible de una alucinacion.

Ofrecer via `AskUserQuestion` dos caminos (sin opcion "persistir igual"):

1. **Re-lanzar `product-teardown`** con instruccion explicita: "Usa WebSearch + WebFetch obligatoriamente en sitio oficial, help center y reviews de {empresa}. Reporta cada URL en `=== FUENTES ===`. Si una pagina esta caida o con login-wall, indicalo y busca alternativas."
2. **Delegar a `browser-navigator`** con objetivo: "Navegar sitio oficial y help center de {empresa}, extraer datos de modulos/features/pricing/integraciones, y devolver un teardown con URLs visitadas y contenido extraido de cada una."

Despues de la re-ejecucion, volver al Paso 2 con el nuevo output y re-evaluar el guardrail.

## Propagacion de completitud

Al finalizar, aplicar la regla de Propagacion de Completitud (ver CLAUDE.md): consultar `"$KB_CLI" todo list --pending`, buscar acciones que matcheen el trabajo completado (por nombre del competidor o producto investigado), y ofrecer completarlas via `"$KB_CLI" todo complete ID`.
