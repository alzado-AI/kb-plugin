---
name: clientes
domain: comercial
tier: basic
description: "Vista 360 de un cliente: oportunidades, contactos, reuniones, tareas, decisiones, documentos, plan de cuenta. Cruza KB + CRM + workspace."
disable-model-invocation: false
---

El usuario quiere ver todo sobre un cliente especifico.

`$ARGUMENTS` es el nombre de la empresa o contacto. Obligatorio.

Si `$ARGUMENTS` esta vacio:
- Preguntar: "¿De que cliente quieres la vista 360?"
- Sugerir los ultimos clientes con actividad reciente

## Contexto organizacional (cargar al arrancar)

Ver `.claude/agents/shared/org-context.md`. Antes de armar la vista 360:

```bash
KB_CLI="kb"
"$KB_CLI" org-context --query "${ARGUMENTS}" --format prompt
"$KB_CLI" legal-entity list --pretty
```

**Reglas de display:**

1. **`Company.tipos[]` es multi-value.** Mostrar TODOS los tipos del cliente (ej: "Hidronor: generador + gestor_integral + competidor"), NO solo `Company.tipo` legacy.
2. **`Position` por contact.** Si una `Person.position` esta seteada, mostrar el nombre de la position en vez del free-text `rol`. Ejemplo: "Jefe de Zona Norte" (Position) vs "encargado del norte" (rol libre).
3. **`LegalEntity` relacionadas.** Si las facturas/contratos del cliente tienen `issuing_legal_entity`, mostrar contra que sociedad del grupo opera el cliente.
4. **Citar reglas/terminos** con `[rule:slug]`/`[term:slug]` cuando el output mencione conceptos o reglas del dominio (ej: "el cliente real es SQ Energia `[rule:mantos-cooper-cliente-real-sq]`").

## Flujo

### 1. Resolver cliente

```bash
KB_CLI="kb"

# Buscar empresa
"$KB_CLI" company list --pretty
# Si no hay match exacto:
"$KB_CLI" search "$ARGUMENTS" --type company --pretty
# Tambien buscar por persona
"$KB_CLI" person find "$ARGUMENTS"
```

Si se encuentra empresa → usar company_id para filtrar todo.
Si se encuentra persona → usar su company_id o listar sus relaciones.

### 2. Recopilar datos (en paralelo)

```bash
# Oportunidades con este cliente
"$KB_CLI" opportunity list --company COMPANY_NAME --pretty

# Plan de cuenta
"$KB_CLI" account-plan list --company COMPANY_NAME --pretty

# Contactos de la empresa
"$KB_CLI" person list --company COMPANY_NAME --pretty

# Tareas pendientes vinculadas (buscar por contexto)
"$KB_CLI" todo find COMPANY_NAME --pending

# Reuniones recientes (buscar por nombre)
"$KB_CLI" meeting search COMPANY_NAME --pretty

# Contratos activos
"$KB_CLI" contract list --company COMPANY_NAME --pretty

# Facturas pendientes/vencidas
"$KB_CLI" invoice list --company COMPANY_NAME --pretty

# Interacciones recientes (ultimos 30 dias)
"$KB_CLI" interaction list --company COMPANY_NAME --since {30_DAYS_AGO} --pretty

# Documentos vinculados
"$KB_CLI" search COMPANY_NAME --type document --pretty

# Decisiones
"$KB_CLI" search COMPANY_NAME --type decision --pretty
```

### 3. Enrichment via providers (opcional)

Si hay CRM provider activo:
- Buscar deals, contacts, actividades del cliente via CLI del provider

Si hay workspace provider activo:
- Buscar emails recientes con contactos del cliente
- Buscar docs compartidos

### 4. Presentar vista 360

```
=== CLIENTE: {company_name} ===
Segmento: {segment} | Ciclo de vida: {lifecycle_stage} | Industria: {industry}

Contactos: N
  - {nombre} ({email}) — {rol}
  - ...

Oportunidades: N (revenue total: $X)
  - {slug}: {titulo} | {estado} | $X | prob: {%}%
  - ...

Plan de Cuenta: {existe/no existe}
  Periodo: {periodo} | Estado: {estado}
  Estrategia: {resumen}

Tareas pendientes: N
  - #{id}: {texto} (prioridad: {alta|media|baja})
  - ...

Reuniones recientes: N
  - {fecha}: {titulo}
  - ...

Documentos: N
  - {nombre} ({tipo})
  - ...

Contratos Activos: N
  - {slug}: {titulo} | Vigencia: {inicio} → {fin} | Valor: $X
  - ...

Facturas Pendientes: N
  - #{id}: $X | Vence: {fecha} | Estado: {estado}
  - ...

Interacciones Recientes (30d): N
  - {fecha}: {tipo} — {resumen}
  - ...

Decisiones: N
  - {texto} ({fecha})
  - ...

⚠ ALERTAS:
  - Contratos por vencer en <30 dias: {lista}
  - Facturas vencidas: {lista con montos}
  - Sin interacciones en 30+ dias: {flag si aplica}
```

### 5. Opciones de accion

Usar AskUserQuestion:

```yaml
question: "¿Que quieres hacer con este cliente?"
options:
  - label: "Crear/actualizar plan de cuenta (Recommended)"
    description: "Lanza account-planner para generar o actualizar el plan estrategico"
  - label: "Crear nueva oportunidad"
    description: "Registrar una nueva oportunidad de venta"
  - label: "Agendar seguimiento"
    description: "Crear tarea de seguimiento con fecha"
  - label: "Solo ver — no hacer nada"
    description: "Vista informativa, sin acciones"
```

Si "Plan de cuenta": lanzar agente `account-planner` (subagent_type="account-planner") con contexto del cliente. Una vez creado el plan, sugerir crear oportunidades vinculadas:
```bash
"$KB_CLI" opportunity create SLUG --company COMPANY_NAME --title "Oportunidad desde plan de cuenta" --owner EMAIL
```

Si "Nueva oportunidad":
```bash
"$KB_CLI" opportunity create SLUG --company COMPANY_NAME --title "..." --owner EMAIL
```

Si "Agendar seguimiento":
```bash
"$KB_CLI" todo create "Seguimiento con COMPANY" --parent-type opportunity --parent-slug SLUG
```
