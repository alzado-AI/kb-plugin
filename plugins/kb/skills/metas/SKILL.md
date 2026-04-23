---
name: metas
domain: core
tier: basic
description: "Progreso vs metas comerciales y financieras. Forecast, gaps, cobertura de pipeline. Compartido entre apps crm y erp."
disable-model-invocation: false
---

El usuario quiere ver progreso contra sus metas (OKRs comerciales, quotas, KPIs financieros).

`$ARGUMENTS` puede ser:
- Vacio: todas las metas del periodo actual
- Periodo: filtrar (ej: `/kb:metas 2026-Q1`)
- Modulo: filtrar por area (ej: `/kb:metas sales`)

## Contexto organizacional (cargar al arrancar)

Ver `.claude/agents/shared/org-context.md`. Antes de armar el dashboard:

```bash
KB_CLI="kb"
"$KB_CLI" org-context --query "metas ${ARGUMENTS}" --format prompt
```

Citar reglas de weighting/forecast/scoring con `[rule:slug]` cuando se apliquen al pipeline coverage o al forecast ponderado. Si las metas mezclan monedas (USD vs CLP) o unidades, usar `kb unit convert` en vez de hardcodear factores.

## Flujo

### 1. Cargar metas y contexto

```bash
KB_CLI="kb"

# Sales goals (metas comerciales) — con oportunidades que respaldan cada meta
"$KB_CLI" sales-goal list --pretty

# Si hay argumento de periodo:
"$KB_CLI" sales-goal list --periodo "$ARGUMENTS" --pretty

# Detalle por meta: que deals la respaldan
# Para cada GOAL_ID relevante:
"$KB_CLI" sales-goal show GOAL_ID --with-opportunities

# Pipeline para forecast
"$KB_CLI" opportunity list --pretty

# Contratos activos (base de revenue recurrente)
"$KB_CLI" contract list --estado activo --pretty

# Outcomes PM (si el pack PM esta activo — metas de producto)
"$KB_CLI" objective list --pretty 2>/dev/null || true
```

### 2. Calcular progreso

Para cada meta:
- Si tiene `actual`: calcular `actual / target * 100` = % de avance
- Si no tiene `actual` pero hay oportunidades vinculadas: calcular forecast ponderado

### 3. Revenue Recognition

Mostrar el flujo de revenue realizado:
```bash
# Deals cerrados (won)
"$KB_CLI" opportunity list --stage closed-won --pretty
# Facturados
"$KB_CLI" invoice list --estado emitida --pretty
# Pagados
"$KB_CLI" invoice list --estado pagada --pretty
```

Presentar como:
```
Revenue Recognition:
  Cerrado → Facturado → Pagado
  $X (N deals)   $Y (N facturas)   $Z (N cobrados)

Revenue Recurrente (contratos activos): $R/mes
```

### 4. Forecast (si hay oportunidades)

Lanzar agente `deal-analyzer` (Agent tool, subagent_type="deal-analyzer") con `--mode forecast` y prompt:

```
Genera forecast para el periodo {periodo}.
Fecha actual: {fecha de hoy}.
```

### 5. Presentar dashboard

```
=== METAS: {periodo} ===

Metas Comerciales:
| Meta | Metric | Target | Actual | Avance | Status |
|------|--------|--------|--------|--------|--------|
| {name} | {metric} | {target} | {actual} | {%}% | {on-track|at-risk|behind} |

Pipeline coverage: {ratio}x ({saludable|riesgoso|critico})
Forecast ponderado: $X (vs target total: $Y)

{Si hay outcomes PM:}
Outcomes de Producto:
| Objective | Metric | Target | Baseline |
|---------|--------|--------|----------|
| {name} | {metric} | {target} | {baseline} |
```

Status rules:
- `on-track`: avance >= dias_transcurridos/dias_totales del periodo (o >=80% del target)
- `at-risk`: avance entre 50% y 80% del ritmo esperado
- `behind`: avance <50% del ritmo esperado

### 6. Opciones de accion

Usar AskUserQuestion:

```yaml
question: "¿Que quieres hacer?"
options:
  - label: "Actualizar progreso de una meta (Recommended)"
    description: "Registrar avance actual en una meta"
  - label: "Crear nueva meta"
    description: "Agregar una meta para el periodo"
  - label: "Ver forecast detallado"
    description: "Lanza deal-analyzer con escenarios"
  - label: "Solo ver — no hacer nada"
    description: "Vista informativa"
```

Si "Actualizar progreso":
```bash
"$KB_CLI" sales-goal update GOAL_ID --actual "VALOR"
```

Si "Crear nueva meta":
```bash
"$KB_CLI" sales-goal create "NOMBRE" --periodo PERIODO --metric METRIC --target TARGET --owner EMAIL
```

Si "Forecast detallado": lanzar `deal-analyzer` con `--mode forecast`

### 7. Propagacion

Despues de actualizar metas:
1. Si avance >= 100%: ofrecer marcar la meta como completada
2. Si pipeline coverage < 2x: sugerir crear tareas de prospeccion
