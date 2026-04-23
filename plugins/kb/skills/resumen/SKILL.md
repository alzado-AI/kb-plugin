---
name: resumen
domain: core
tier: basic
description: "Generar resumen integral de la base de conocimiento del producto, cruzando Linear, acciones, preguntas, reuniones y discovery."
disable-model-invocation: false
---

El usuario quiere un resumen ejecutivo integral de su base de conocimiento.

## Bloque "Salud del dominio" (white-label)

Antes de delegar a kb-resumen, recolectar metricas de salud del dominio para incluirlas en el resumen ejecutivo:

```bash
KB_CLI="kb"
"$KB_CLI" organization coverage --pretty
"$KB_CLI" organization onboarding --pretty
```

En el resumen final, agregar una seccion `## Salud del dominio` con:
- **Conteos**: terms (total + por tipo), rules (active + applied_last_30d), processes, legal_entities.
- **Coverage**: % de smoke tests passing, top 5 reglas mas usadas en el periodo, top 5 terminos mas usados.
- **Onboarding**: % completo + proximo item del checklist.

Si hay drift findings o conflicts pendientes, mencionarlos como "items que necesitan atencion del PM".

## Paso 1: Obtener datos

Usa el agente `kb-resumen` (Agent tool, subagent_type="kb-resumen") para leer fuentes, consultar Linear CLI, clasificar por modulo y retornar datos estructurados.

```
Genera un resumen ejecutivo de la base de conocimiento. Fecha actual: {fecha de hoy}.
{Si $ARGUMENTS tiene contenido: "Alcance: solo el producto $ARGUMENTS."}
{Si $ARGUMENTS esta vacio: "Alcance: todos los productos."}
```

Si el usuario incluyo argumentos (ej: `/kb:resumen Accounting`, `/kb:resumen contabilidad`, `/kb:resumen CxC`), pasalos como filtro al agente. Acepta nombre en espanol o ingles.

El agente devuelve datos estructurados (secciones `=== META ===`, `=== MODULO: X ===`, `=== TABLA RESUMEN ===`), NO output formateado.

## Paso 2: Formatear output

Tomar los datos del agente y renderizarlos con este template:

```
# Resumen Ejecutivo — {fecha de META}

## {Nombre del modulo}
**PM:** {pm} | **EM:** {em}

### Estado en el project tracker
- {cada linea del project tracker}
{Si project_tracker_disponible = "no": "Project tracker no disponible."}

### Acciones Pendientes
- {cada linea de acciones}

### Preguntas Abiertas
- {cada linea de preguntas}

### Reuniones Recientes
- {cada linea de reuniones}

### Discovery / Decisiones
- {cada linea de discovery}

(repetir bloque ## por cada MODULO del output del agente)

---

## Resumen General

| Producto | Proyectos Activos | Acciones | Preguntas | Reuniones (7d) |
|----------|-------------------|----------|-----------|----------------|
| {modulo} | {proyectos} | {acciones} | {preguntas} | {reuniones} |

(una fila por linea de TABLA RESUMEN)

**Datos project tracker**: {si project_tracker_disponible = "si": "en vivo via CLI" | sino: "no disponible"}
```

Reglas de formateo:
- Omitir subsecciones vacias dentro de cada modulo (si el agente no devolvio `acciones:` para un modulo, no mostrar "### Acciones Pendientes")
- Omitir modulos completamente vacios
- Si el agente devuelve secciones inesperadas o formato raro, mostrar el output raw del agente como fallback
