---
name: contratos
domain: comercial
tier: basic
description: "Gestion de contratos: vista por estado, alertas de renovacion, crear/renovar/cancelar. Cruza con oportunidades, facturas y plan de cuenta."
disable-model-invocation: false
---

El usuario quiere gestionar contratos con clientes.

`$ARGUMENTS` puede ser:
- Vacio: vista completa de contratos agrupados por estado
- Nombre de empresa: filtrar por cliente (ej: `/kb:contratos acme`)

## Contexto organizacional (cargar al arrancar)

Ver `.claude/agents/shared/org-context.md`. Antes de listar contratos:

```bash
KB_CLI="kb"
"$KB_CLI" org-context --query "contratos ${ARGUMENTS}" --format prompt
"$KB_CLI" legal-entity list --pretty
```

Si los contratos del cliente tienen `issuing_legal_entity`, **agrupar y reportar por sociedad del grupo** (ej: "Contratos emitidos por Bravo Energy SPA: 3 / Combustibles Becsa: 1"). Citar reglas de renovacion/cancelacion activas con `[rule:slug]`. Al crear un contrato nuevo, sugerir asociar `issuing_legal_entity` cuando aplique.

## Flujo

### 1. Cargar contratos

```bash
KB_CLI="kb"

# Si hay argumento (nombre de empresa):
"$KB_CLI" contract list --company "$ARGUMENTS" --pretty

# Si no hay argumento: todos los contratos
"$KB_CLI" contract list --pretty
```

### 2. Agrupar por estado

Presentar contratos agrupados:

```
=== CONTRATOS ===

ACTIVOS: N ($X total)
  - {slug}: {titulo} | {company} | Vigencia: {inicio} → {fin} | Valor: $X/periodo
  - ...

POR RENOVAR (proximos 90 dias): N
  - {slug}: {titulo} | {company} | Vence: {fecha} | Valor: $X
  - ...

VENCIDOS: N
  - {slug}: {titulo} | {company} | Vencio: {fecha} | Valor: $X
  - ...
```

### 3. Alertas de renovacion

```bash
# Contratos que vencen pronto
"$KB_CLI" contract list --estado activo --pretty
```

Filtrar y clasificar por urgencia:
- **CRITICO** (< 30 dias): requiere accion inmediata
- **ATENCION** (30-60 dias): iniciar conversacion de renovacion
- **PLANIFICAR** (60-90 dias): agendar revision

```
ALERTAS DE RENOVACION:
  CRITICO (< 30d):
    - {slug}: {company} — vence {fecha} ({N} dias) — $X
  ATENCION (30-60d):
    - {slug}: {company} — vence {fecha} ({N} dias) — $X
  PLANIFICAR (60-90d):
    - {slug}: {company} — vence {fecha} ({N} dias) — $X
```

### 4. Cross-links

Para cada contrato relevante, mostrar relaciones:

```bash
# Oportunidad vinculada
"$KB_CLI" opportunity list --company COMPANY_NAME --pretty

# Facturas del contrato
"$KB_CLI" invoice list --company COMPANY_NAME --pretty

# Plan de cuenta
"$KB_CLI" account-plan list --company COMPANY_NAME --pretty
```

Presentar como:
```
Cross-links ({company}):
  Oportunidad: {slug} | {estado} | $X
  Facturas: N pendientes ($X) | N pagadas ($Y)
  Plan de cuenta: {existe/no existe}
```

### 5. Opciones de accion

Usar AskUserQuestion:

```yaml
question: "¿Que quieres hacer?"
options:
  - label: "Renovar contrato (Recommended)"
    description: "Crear nuevo contrato basado en uno existente, con fechas actualizadas"
  - label: "Crear nuevo contrato"
    description: "Registrar un contrato nuevo"
  - label: "Actualizar estado"
    description: "Cambiar estado de un contrato (activo, suspendido, cancelado, vencido)"
  - label: "Cancelar contrato"
    description: "Marcar un contrato como cancelado"
  - label: "Solo ver — no hacer nada"
    description: "Vista informativa"
```

Si "Renovar contrato":
```bash
# Mostrar contrato actual
"$KB_CLI" contract show SLUG --pretty
# Crear nuevo basado en el existente (copiar datos, nuevas fechas)
"$KB_CLI" contract create NUEVO_SLUG --company COMPANY_NAME --title "Renovacion: {titulo}" --start-date NUEVA_FECHA --end-date NUEVA_FECHA --amount MONTO
# Marcar el anterior como vencido/completado
"$KB_CLI" contract update SLUG --estado vencido
```

Si "Crear nuevo contrato":
```bash
"$KB_CLI" contract create SLUG --company COMPANY_NAME --title "..." --start-date FECHA --end-date FECHA --amount MONTO
```

Si "Actualizar estado":
```bash
"$KB_CLI" contract update SLUG --estado NUEVO_ESTADO
```

Si "Cancelar contrato":
```bash
"$KB_CLI" contract update SLUG --estado cancelado
```

### 6. Propagacion

Despues de cualquier accion:
1. Si se renueva: ofrecer crear oportunidad vinculada para el nuevo periodo
2. Si se cancela: buscar facturas pendientes del contrato, alertar si hay
3. `"$KB_CLI" todo list --pending` — buscar tareas de contrato relacionadas, ofrecer completar
