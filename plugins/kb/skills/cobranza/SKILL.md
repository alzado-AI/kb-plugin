---
name: cobranza
domain: finanzas
tier: basic
description: "Estado de cuentas por cobrar, facturas vencidas, acciones de cobranza. Lee KB + analytics provider."
disable-model-invocation: false
---

El usuario quiere ver el estado de cobranza / cuentas por cobrar.

`$ARGUMENTS` puede ser:
- Vacio: vista completa de cobranza
- Nombre de cliente: filtrar por empresa (ej: `/kb:cobranza acme`)

## Contexto organizacional (cargar al arrancar)

Ver `.claude/agents/shared/org-context.md`. Antes de listar facturas:

```bash
KB_CLI="kb"
"$KB_CLI" org-context --module receivables --query "cobranza ${ARGUMENTS}" --format prompt
"$KB_CLI" legal-entity list --pretty   # sociedades del grupo (filtrar facturas por issuing_legal_entity cuando aporte)
```

Citar inline cualquier regla de aging/cobranza/exclusion que aplique: `[rule:slug]`. Para reportar montos cruzando monedas, usar `kb unit convert AMOUNT FROM TO --context '{...}'` en vez de hardcodear factores. Si una factura tiene `issuing_legal_entity`, segmentar el reporte por sociedad cuando aporte (ej: "facturas emitidas por bravo-spa vs combustibles-becsa").

## Flujo

### 1. Vista rapida

```bash
KB_CLI="kb"

# Facturas vencidas
"$KB_CLI" invoice list --overdue --pretty

# Si hay filtro por cliente:
# "$KB_CLI" invoice list --company "$ARGUMENTS" --estado vencida --pretty
# "$KB_CLI" cashflow list --company "$ARGUMENTS" --pretty

# Cashflow items pendientes (ingresos)
"$KB_CLI" cashflow list --tipo ingreso --pretty

# Tareas de cobranza pendientes
"$KB_CLI" todo find "pago" --pending
```

### 2. Gestion de facturas

Si hay filtro por cliente:
```bash
"$KB_CLI" invoice list --company "$ARGUMENTS" --estado vencida --pretty
```

Si no hay facturas para un cliente con cashflow pendiente, ofrecer crearla:
```bash
"$KB_CLI" invoice create --company COMPANY_NAME --amount X --due-date FECHA --description "..."
```

### 3. Analisis profundo

Lanzar agente `financial-analyst` (Agent tool, subagent_type="financial-analyst") con `--mode collections` y prompt:

```
Genera reporte de estado de cobranza.
{Si hay filtro: "Foco en cliente: $ARGUMENTS"}
Fecha actual: {fecha de hoy}.
```

### 4. Revenue Pipeline (cross-link)

Mostrar flujo completo de revenue:
```bash
# Deals en negociacion
"$KB_CLI" opportunity list --stage negotiation --pretty
# Facturados
"$KB_CLI" invoice list --estado emitida --pretty
# Pagados
"$KB_CLI" invoice list --estado pagada --pretty
```

Presentar como:
```
Revenue Pipeline:
  Negociacion → Facturado → Pagado
  $X (N deals)   $Y (N facturas)   $Z (N pagos)
```

### 5. Presentar reporte

Mostrar output del financial-analyst. Destacar:
- Alertas ALTO primero (facturas >90d)
- Total vencido vs total por cobrar
- DSO si hay datos analytics

### 6. Opciones de accion

Usar AskUserQuestion:

```yaml
question: "¿Que quieres hacer?"
options:
  - label: "Crear tareas de seguimiento (Recommended)"
    description: "Crear tasks para facturas vencidas sin seguimiento activo"
  - label: "Registrar ingreso recibido"
    description: "Marcar un cashflow item como ejecutado"
  - label: "Ver estado financiero completo"
    description: "Lanza financial-analyst para vista integral"
  - label: "Solo ver — no hacer nada"
    description: "Vista informativa"
```

Si "Crear tareas":
```bash
"$KB_CLI" todo create "Seguimiento cobranza: {detalle}" --parent-type budget --parent-slug SLUG
```

Si "Registrar ingreso":
- Preguntar cual cashflow item → actualizar estado a "ejecutado"

Si "Estado financiero": lanzar `financial-analyst`

### 7. Propagacion

Despues de cualquier accion:
1. `"$KB_CLI" todo list --pending` — buscar tareas de cobranza completadas
2. Ofrecer marcar como completadas
