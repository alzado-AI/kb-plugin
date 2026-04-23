---
name: tutorial
domain: core
tier: basic
description: "Guia dinamica del sistema. Sin argumentos: panorama completo personalizado al estado actual de tu KB. Con argumento: deep dive en un skill o concepto (ej: /tutorial ost, /tutorial dev, /tutorial primeros-pasos)."
---

## Paso 1: Obtener datos

Lanza el agente `tutorial-guide` (Agent tool, subagent_type="tutorial-guide"):

```
Agent(
  subagent_type="tutorial-guide",
  prompt="Generar tutorial del sistema. Tema: {$ARGUMENTS o 'ninguno — panorama completo'}"
)
```

El agente devuelve datos estructurados (secciones `=== META ===`, `=== ESTADO ===`, etc.), NO output formateado.

## Paso 2: Formatear output

Detectar `modo` en la seccion META del agente y aplicar el template correspondiente.

### Si modo = panorama

```
# Tutorial del Sistema — {YYYY-MM-DD}
Hola {nombre_usuario de ESTADO}

## El Sistema en 1 Minuto

El sistema cubre el ciclo completo de un PM de producto:

Problema llega → Gestionar oportunidades → Trabajar features → Gestionar tiempo
    /analiza         /estrategia              /project               /matriz
                     /program                  /project            /pendientes

Cada skill tiene un proposito especifico. No son alternativas — son vistas complementarias.

## Tu Estado Actual

| Componente | Estado | Accion |
|-----------|--------|--------|
(para cada item en COMPONENTES: | {componente} | {estado} | {accion} |)

## Skills por Categoria

(para cada categoria en SKILLS:)
### {categoria}
(para cada skill en la categoria:)
- `{skill}` — {descripcion}

## Flujos Recomendados

(para cada flujo en FLUJOS:)
### {titulo}
{pasos, reemplazar " → " con saltos de linea numerados}

## Por Donde Empezar

{texto de RECOMENDACION}
```

### Si modo = deep_dive

```
# Tutorial: {tema de META} — {YYYY-MM-DD}

## Que es y para que sirve
{que_es de DEEP DIVE}

## Cuando usarlo
{cuando_usarlo de DEEP DIVE}

## Como funciona (paso a paso)
{pasos de DEEP DIVE}

## Comandos de practica
{comandos de DEEP DIVE}

## Errores comunes
{errores de DEEP DIVE}

## Conecta con
{conecta_con de DEEP DIVE}
```

Reglas de formateo:
- Si el agente devuelve secciones inesperadas o formato raro, mostrar el output raw del agente como fallback
- Todo en espanol

## Temas disponibles para deep dive

| Argumento | Cubre |
|-----------|-------|
| `primeros-pasos` | Onboarding al sistema, flujo inicial |
| `ost` / `rice` / `priorizacion` | OST framework de PODA, RICE, outcomes |
| `matriz` / `eisenhower` / `tiempo` | Eisenhower, Q1-Q4, gestion del tiempo del PM |
| `analiza` / `triaje` / `challenge` | Workflow de triaje: challengear problemas antes de actuar |
| `project`, `solucion`, `ciclo`, `feature`, `lifecycle` | Workshop de ejecucion, ciclo de vida del feature |
| `dev` | Pipeline issue → PR con gates (estacion DEV de /project) |
| `batman`, `fix`, `issue` | Workshop de fix rapido end-to-end |
| `comite`, `comite de producto` | Workflow de comite: revisar issues en Triage, investigar antecedentes, decidir destino |
| `refinar`, `refinamiento`, `backlog` | Workflow de refinamiento: completar issues en Backlog con spec dev-ready |
| `audit`, `spec-vs-code` | Comparar spec vs codigo implementado |
| `program`, `oportunidad`, `exploracion` | Workshop de exploracion de oportunidades |
| `flujos` | 5-6 flujos completos end-to-end |
| `figma`, `diseno`, `diseño` | Estacion DISEÑO: GENERAR/LEER/SYNC |
| `trabajar` / `trabajo` / `scan` / `prioridades` | Scanner de trabajo |
| `{nombre de skill}` | Explicacion detallada con ejemplos |
