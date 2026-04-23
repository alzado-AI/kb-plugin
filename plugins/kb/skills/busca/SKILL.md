---
name: busca
domain: core
tier: basic
description: "Buscar informacion por tema cruzando Google Chat, Gmail, Drive, Calendar, project tracker, GitHub e internet. Siempre incluye Reuniones KB local. Acepta keyword, rango de fechas y filtro de fuentes: /kb:busca conciliacion, /kb:busca cheques desde:2026-02-01, /kb:busca facturas en:google,tracker,internet."
disable-model-invocation: false
---

El usuario quiere buscar informacion sobre un tema cruzando multiples fuentes: Google Workspace (Chat, Gmail, Drive), Linear y codigo (GitHub).

## Fase 1 — Parsear argumentos

Extrae de `$ARGUMENTS`:

- **keyword**: el tema a buscar (obligatorio). Ej: `/kb:busca conciliacion` → keyword = "conciliacion"
- **desde**: fecha inicio opcional. Ej: `/kb:busca cheques desde:2026-02-01` → desde = 2026-02-01
- **en**: fuentes especificas. Ej: `/kb:busca facturas en:google,tracker` → fuentes = [google, tracker]
  - Valores validos: `google` (Chat+Gmail+Drive), `tracker` (project tracker), `codigo` (GitHub), `intercom` (tickets y articulos), `calendar`, `internet` (busqueda web publica), `todas`
- **todo**: ignora watermarks. Ej: `/kb:busca cheques todo` → buscar_todo = true

Si no hay keyword (solo `/kb:busca`), pregunta que quiere buscar.

## Fase 2 — Determinar fuentes

**Nota:** `Reuniones KB` (via `"$KB_CLI" meeting search`) siempre se incluye, independiente de la seleccion.

Si `en:` NO fue especificado, pregunta usando AskUserQuestion:
- Pregunta: "Donde quieres buscar '{keyword}'?"
- Opciones:
  1. Google (Chat + Gmail + Drive) (Recommended)
  2. Project Tracker (issues y comentarios)
  3. Codigo (repos GitHub)
  4. Calendar (eventos de Google Calendar)
  5. Intercom (tickets y articulos Help Center)
  6. Internet (busqueda web publica)
  7. Todas las fuentes

Valores validos para `en:`: `google`, `tracker`, `codigo`, `calendar`, `intercom`, `internet`, `todas`

Si `en:` fue especificado, usar directamente sin preguntar.

## Fase 3 — Lanzar busquedas en paralelo

Lanza TODOS los agentes/herramientas que apliquen **en un solo response** (multiples Agent tool calls en paralelo).

### Fuente: Reuniones KB (SIEMPRE activa)

Buscar directamente en la KB local via CLI, independiente de las fuentes seleccionadas:
1. `"$KB_CLI" meeting search "{keyword}"`
2. Si hay matches: mostrar los 5 mas recientes con contenido relevante
3. Si no hay matches: reportar "Sin resultados en Reuniones KB"

### Fuente: Google (Chat + Gmail + Drive)
Lanzar agente `external-searcher`:
```
Agent tool:
  subagent_type: "external-searcher"
  prompt: "Busca informacion sobre '{keyword}' en Google Workspace.
    Fuentes: gmail, drive, chat (todas las de Google).
    Dias atras: {days_back o calcular desde 'desde:'}.
    {Si buscar_todo: 'Ignora watermarks, busca desde el inicio.'}
    Devuelve resultados organizados por fuente con tablas."
```

Si `desde:` fue especificado, calcular `days_back` como diferencia entre hoy y la fecha.
Si no, default 30 dias.

### Fuente: Project Tracker
Use the active **project-tracker provider** to search for `"{keyword}"`, optionally scoped to a team.
If no team is known (search without module context), search without team scope — this may only return docs (issue search may require team). Note: issue search may be client-side depending on the provider.

### Fuente: Calendar (si en:calendar o en:todas)

Use the active **workspace provider** to search calendar events for `"{keyword}"` looking back `{days_back or 90}` days.
Mostrar: titulo del evento, fecha, duracion, participantes principales.

### Fuente: Codigo
Lanzar agente `codebase-navigator`:
```
Agent tool:
  subagent_type: "codebase-navigator"
  prompt: "Busca en el codebase del producto todo lo relacionado con '{keyword}'.
    Busca en: nombres de archivos, contenido de codigo, PRs recientes, issues.
    Resume los hallazgos principales de forma concisa para un PM."
```

### Fuente: Intercom (tickets y articulos)

Ejecutar directamente (2 busquedas en paralelo):

1. **Conversaciones:**
   `mcp__claude_ai_Intercom__search(query="object_type:conversations source_subject:contains:\"{keyword}\" limit:10")`
   Si pocos resultados, complementar con `source_body:contains`.
   Para los 3-5 mas relevantes: `mcp__claude_ai_Intercom__get_conversation(id=...)`

2. **Articulos Help Center:**
   `mcp__claude_ai_Intercom__search_articles(phrase="{keyword}", state="published", highlight=true)`

Mostrar: titulo, estado (open/closed), fecha, cliente, resumen del problema.

**Graceful degradation:** Si Intercom MCP no esta configurado o falla, saltar silenciosamente y reportar "Intercom no disponible" en resultados. Nunca bloquear el flujo.

### Fuente: Internet (busqueda web publica)

Buscar directamente con WebSearch:
```
WebSearch(query="{keyword} {contexto adicional si lo hay}")
```

**Query crafting:** Usar el keyword del usuario. Si el keyword es muy corto (1 palabra), enriquecerlo con contexto de dominio del producto (ej: "conciliacion" → "conciliacion bancaria automatica software contable"). Si el keyword ya es descriptivo, usarlo tal cual.
Presentar: titulo, snippet, URL de los resultados mas relevantes (max 5).
**Graceful degradation:** Si WebSearch falla o no devuelve resultados relevantes, saltar silenciosamente y reportar "Internet: sin resultados relevantes" en resultados. Nunca bloquear el flujo.

## Fase 4 — Sintetizar resultados

Al recibir resultados de todos los agentes/herramientas:

1. **Presentar organizados por fuente** — usar el formato de cada fuente tal cual llega
2. **Resumen ejecutivo** (3-5 lineas):
   - Que se encontro en total
   - Donde esta la informacion mas relevante
   - Quienes participaron en las discusiones
   - Temas principales que tocan
3. **Highlight**: los 3-5 hallazgos mas relevantes, con links/IDs para profundizar

Formato:
```
## Busqueda: "{keyword}"

### Resumen ejecutivo
[3-5 lineas cruzando todas las fuentes]

### Resultados por fuente

#### Reuniones KB
[Reuniones encontradas via CLI con extractos relevantes, o "Sin resultados"]

#### Google Workspace
[Output del external-searcher]

#### Calendar
[Eventos encontrados: titulo, fecha, duracion, participantes — solo si en:calendar o en:todas]

#### Project Tracker
[Resultados de issues y docs]

#### Intercom
[Tickets encontrados: titulo, estado, fecha, cliente, resumen — solo si en:intercom o en:todas]

#### Internet
[Resultados de busqueda web: titulo, snippet, URL — solo si en:internet o en:todas]

#### Codigo
[Output del codebase-navigator]

### Hallazgos destacados
1. [Hallazgo mas relevante + fuente + link]
2. ...
```

## Fase 5 — Acciones de seguimiento

Despues de mostrar resultados, ofrece 3 opciones usando AskUserQuestion:

1. **Profundizar** — "Quieres que lea algun email, thread, documento o issue completo?"
2. **Persistir en KB** — "Quieres que guarde estos hallazgos en la base de conocimiento?" (via KB CLI directo: `kb learning create`, `kb todo create`, etc.)
3. **Refinar busqueda** — "Quieres buscar con otros terminos o en otras fuentes?"
4. **Listo** — No hacer nada mas

Si elige profundizar, lanzar el agente correspondiente para leer el item completo.
Si elige persistir:
  1. Clasificar y guardar directamente via KB CLI (`kb learning create`, `kb todo create`, `kb question create`, etc. segun el tipo de hallazgo).
  2. **Despues de persistir exitosamente**, relanzar `external-searcher` con prompt:
     `"actualizar_watermarks: true. Keyword: '{keyword}'. Actualiza los watermarks con estas fechas: {fechas del ultimo item por fuente}."`
     Esto asegura que los watermarks solo avanzan cuando la info fue guardada.
Si elige refinar, volver a Fase 1 con los nuevos terminos.
