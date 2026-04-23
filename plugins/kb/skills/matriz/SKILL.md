---
name: matriz
domain: core
description: "Vista Eisenhower 2D de tareas del PM (urgencia x importancia). Gestiona el tiempo del PM, NO prioriza oportunidades. Senala modo reactivo si Q2 esta vacio."
---

Lanza el agente `matriz-eisenhower` pasandole el argumento del usuario como filtro de modulo.

## Entrada

`$ARGUMENTS` puede ser:
- Vacio: clasificar todas las tareas pendientes (via `kb todo list --pending`)
- Nombre de modulo: filtrar por modulo (ej: `accounting`, `receivables`, `general`)

## Paso 1: Obtener datos

```
Agent(
  subagent_type="matriz-eisenhower",
  prompt="Generar matriz Eisenhower de tareas del PM. Filtro de modulo: {$ARGUMENTS o 'ninguno — mostrar todo'}"
)
```

El agente devuelve datos estructurados (secciones `=== META ===`, `=== Q1 ===`, etc.), NO output formateado.

## Paso 2: Formatear output

Tomar los datos del agente y renderizarlos con este template:

```
# Matriz Eisenhower — {fecha de META}
{Si filtro != "ninguno": "Modulo: {filtro}"}

## Q1 — Hacer Ahora (Urgente + Importante)
| Tarea | Razon urgencia | Razon importancia |
|-------|----------------|-------------------|
| {tarea} | {urgencia} | {importancia} |

## Q2 — Bloquear Tiempo (Importante + No Urgente)
*Trabajo estrategico — reservar bloques dedicados en el calendario*
| Tarea | Por que importa |
|-------|----------------|
| {tarea} | {importancia} |

## Q3 — Delegar o Minimizar (Urgente + No Importante)
| Tarea | Accion sugerida |
|-------|----------------|
| {tarea} | {accion} |

## Q4 — Eliminar o Diferir
| Tarea | Motivo |
|-------|--------|
| {tarea} | {motivo} |

---
Q1:{q1_count} | Q2:{q2_count} | Q3:{q3_count} | Q4:{q4_count}
`/estrategia` para vista estrategica | `/pendientes` para lista por tiers
```

Reglas de formateo:
- Omitir cuadrantes vacios (no mostrar seccion ni tabla)
- Si `q2_count` < 2 de META, agregar warning despues del footer:
  ```
  Posible modo reactivo — poco tiempo dedicado a trabajo estrategico.
  Considera reservar bloques para discovery, decisiones de producto y OKRs.
  ```
- Si el agente devuelve secciones inesperadas o formato raro, mostrar el output raw del agente como fallback

## Referencia de cuadrantes

| | Urgente | No Urgente |
|--|---------|------------|
| **Importante** | Q1: Hacer Ahora | Q2: Bloquear Tiempo |
| **No Importante** | Q3: Delegar/Batch | Q4: Eliminar/Diferir |

**Q2 es donde vive el trabajo estrategico.**
