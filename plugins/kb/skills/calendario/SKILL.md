---
name: calendario
domain: core
tier: basic
description: "Navegar el calendario: agenda, busqueda, prep de reuniones y sync. /kb:calendario semana, /kb:calendario busca standup, /kb:calendario prepara nombre, /kb:calendario sync"
disable-model-invocation: false
---

El usuario quiere interactuar con su calendario de Google. El skill tiene varios modos segun los argumentos.

## Fase 1 — Parsear modo desde `$ARGUMENTS`

Detectar modo segun el primer token de `$ARGUMENTS`:

| Argumento | Modo |
|-----------|------|
| (vacio) | DEFAULT — agenda hoy + proximos 3 dias |
| `semana` | SEMANA — proximos 7 dias |
| `pasada` o `ayer` | PASADA — ultimos 7 dias |
| `busca {keyword}` | BUSCA — buscar eventos por keyword |
| `prepara {keyword}` | PREPARA — contextualizar reunion proxima |
| `revisar {keyword}` o `review {keyword}` | REVISAR — revisar notas y docs de reuniones pasadas |
| `sync` | SYNC — pipeline: calendar-discoverer → meeting-parser → gate → meeting-persister |

Si el argumento no matchea ninguno de los anteriores, tratar como keyword del modo BUSCA.

Hoy es: usar la fecha actual del sistema (no asumir fecha fija).

---

## Modo DEFAULT — Agenda proximos 3 dias

1. Use the active **workspace provider** to list calendar events with:
   - `time_min` = hoy T00:00:00 (en timezone local, Chile/Santiago = UTC-3)
   - `time_max` = hoy + 3 dias T23:59:59
   - `max_results` = 20

2. Formatear como agenda limpia:

```
## Agenda — {fecha inicio} al {fecha fin}

### {DIA, DD de Mes}
- HH:MM — HH:MM  {Titulo del evento}
  Asistentes: {nombres clave, max 4, si hay mas: "+ N mas"}
  {Si tiene attachments: "Adjuntos: {N} doc(s)"}

### {DIA siguiente}
...
```

Si no hay eventos: "Sin eventos en los proximos 3 dias."

3. Gate con AskUserQuestion:
   - Pregunta: "Que quieres hacer?"
   - Opciones:
     - `[P]` Preparar una reunion de la lista
     - `[B]` Buscar un evento especifico
     - `[S]` Sync reuniones pasadas a KB
     - `[X]` Listo

---

## Modo SEMANA — Vista 7 dias

1. Use the active **workspace provider** to list calendar events with:
   - `time_min` = hoy T00:00:00
   - `time_max` = hoy + 7 dias T23:59:59
   - `max_results` = 50

2. Mismo formato de agenda limpia que modo DEFAULT, agrupado por dia.

3. Gate identico al modo DEFAULT.

---

## Modo PASADA — Ultimos 7 dias

1. Use the active **workspace provider** to list calendar events with:
   - `time_min` = hoy - 7 dias T00:00:00
   - `time_max` = hoy - 1 dia T23:59:59
   - `max_results` = 50

2. Mismo formato de agenda, agrupado por dia (cronologico descendente: mas reciente primero).

3. Gate con AskUserQuestion:
   - Pregunta: "Que quieres hacer?"
   - Opciones:
     - `[S]` Sync estas reuniones a KB (pipeline: calendar-discoverer → meeting-parser → gate → meeting-persister)
     - `[P]` Preparar contexto de una reunion pasada
     - `[R]` Revisar notas de una reunion (modo REVISAR)
     - `[X]` Listo

---

## Modo BUSCA — Buscar eventos por keyword

Keyword = todo lo que siga a `busca ` en `$ARGUMENTS`.

1. Use the active **workspace provider** to search calendar events with:
   - `query` = keyword
   - `days_back` = 90 (buscar pasado y futuro cercano)

2. Mostrar resultados:

```
## Busqueda: "{keyword}"

Encontrados: N eventos

| Fecha | Hora | Titulo | Asistentes |
|-------|------|--------|------------|
| ...   | ...  | ...    | ...        |
```

Si no hay resultados: "No se encontraron eventos con '{keyword}' en los ultimos 90 dias."

3. Gate con AskUserQuestion:
   - Pregunta: "Que quieres hacer con estos resultados?"
   - Opciones:
     - `[P]` Preparar contexto de uno de estos eventos
     - `[X]` Listo

---

## Modo PREPARA — Contextualizar una reunion

Keyword = todo lo que siga a `prepara ` en `$ARGUMENTS`.

Pipeline de 2 agentes: **meeting-researcher** (investigacion multi-fuente) → **meeting-synthesizer** (sintesis + agenda).

### Paso 1: Encontrar el evento

Use the active **workspace provider** to search calendar events for `"{keyword}"` looking back 7 days.

Preferir eventos futuros. Si hay varios, elegir el mas proximo (fecha mas cercana a hoy hacia adelante). Si no hay futuro, tomar el mas reciente pasado.

Si no se encuentra ningun evento: notificar y terminar.

### Paso 2: Obtener detalle del evento

Use the active **workspace provider** to show the full event detail for `{event_id_encontrado}`.

Extraer del evento:
- Titulo, fecha, hora, duracion
- Descripcion (puede tener agenda pre-armada o links)
- Lista completa de asistentes con emails
- Adjuntos: lista de Google Docs adjuntos (file_id + nombre)

### Paso 2.5: Gate de periodo

AskUserQuestion:
- Pregunta: "¿Que periodo quieres revisar para '{titulo del evento}'?"
- Opciones:
  - `[1]` Ultima semana (7 dias)
  - `[2]` Ultimas 2 semanas
  - `[3]` Ultimo mes
  - `[C]` Personalizado (especifica fechas o rango)

### Paso 2.7: Leer GDocs + extraer keywords y compromisos

**Si hay adjuntos:**

Para cada Google Doc adjunto, leer via workspace provider:
```bash
kb google drive export "{file_id}" "/tmp/meeting-prep-{file_id}.docx"
```
Leer el contenido exportado. Guardar como `GDOC_CONTENT` (texto completo concatenado de todos los docs).

Extraer del contenido del GDoc:
1. **KEYWORDS_ENRIQUECIDOS** = keywords del titulo/descripcion + clientes/proyectos activos mencionados en el GDoc + personas del equipo con temas abiertos + features recurrentes. Regla: si un termino aparece en >=2 sesiones del GDoc, es keyword obligatorio.
2. **COMPROMISOS_PREVIOS** = lista de compromisos y decisiones de sesiones anteriores: quien se comprometio a que, que se decidio, que quedo abierto. Marcar fecha de cada compromiso si es inferible.
3. **TIPO_REUNION** = clasificar segun asistentes + titulo:
   - `equipo`: 3+ miembros del mismo equipo (Bi-Weekly, Sprint Review, Team sync)
   - `1:1`: 2 personas, o reunion sobre feature/decision especifica
   - `externa`: asistentes externos al equipo (demo, QBR, cliente)

**Si no hay adjuntos:**
- `GDOC_CONTENT` = "ninguno"
- `KEYWORDS_ENRIQUECIDOS` = keywords del titulo y descripcion del evento
- `COMPROMISOS_PREVIOS` = "ninguno"
- `TIPO_REUNION` = inferir solo de asistentes + titulo

**MODULO**: inferir del titulo del evento:
- "Accounting" en titulo → "accounting"
- "Receivables" en titulo → "receivables"
- "Procurement" / "CxP" en titulo → "procurement"
- "Expense" / "Rendiciones" en titulo → "expense-management"
- Si no es obvio del titulo: inferir de los asistentes via `"$KB_CLI" person list` + `"$KB_CLI" team list`

### Paso 3: Delegar a meeting-researcher

```
Agent tool:
  subagent_type: "meeting-researcher"
  prompt: |
    EVENTO: {titulo} | {fecha} {hora} | Duracion: {duracion}
    DESCRIPCION_EVENTO: {descripcion completa del evento, si tiene}
    ASISTENTES: {lista completa con emails}
    PERIODO_REVISION: {periodo elegido en paso 2.5}
    KEYWORDS_ENRIQUECIDOS: {keywords enriquecidos del paso 2.7}
    TIPO_REUNION: {tipo del paso 2.7}
    MODULO: {modulo inferido del paso 2.7}

    Investiga TODAS las fuentes disponibles para contextualizar esta reunion.
```

El agente devuelve hallazgos categorizados (secciones `=== AVANCES ===`, `=== TRABADOS ===`, etc.), NO output formateado ni agenda.

### Paso 4: Delegar a meeting-synthesizer

```
Agent tool:
  subagent_type: "meeting-synthesizer"
  prompt: |
    EVENTO: {titulo} | {fecha} {hora} | Duracion: {duracion} | Asistentes: {lista con roles}
    GDOC_CONTENT: |
      {texto completo de los GDocs del paso 2.7, o "ninguno"}
    COMPROMISOS_PREVIOS: |
      {compromisos extraidos en paso 2.7, o "ninguno"}
    HALLAZGOS: |
      {output completo del meeting-researcher del paso 3}
    TIPO_REUNION: {tipo del paso 2.7}

    Sintetiza la preparacion de esta reunion: sesiones anteriores, compromisos incumplidos, agenda sugerida y preguntas recomendadas.
```

El agente devuelve la sintesis estructurada (secciones `=== META ===`, `=== COMPROMISOS INCUMPLIDOS ===`, `=== AGENDA SUGERIDA ===`, etc.).

### Paso 4.5: Formatear output combinado

Combinar output del researcher (hallazgos) y synthesizer (sintesis) en un template unificado:

```
## Preparacion: {titulo de META}

### Detalles
- Fecha: {fecha}
- Duracion: {duracion}
- Asistentes: {asistentes}
- Docs adjuntos: {adjuntos}
{Si agenda_evento != "ninguna": "- Agenda del evento: {agenda_evento}"}

---

### Sesiones anteriores
{texto de SESIONES ANTERIORES del synthesizer}

{Si hay seccion COMPROMISOS INCUMPLIDOS:}
**Compromisos incumplidos:**
{para cada item: "- {item}"}

---

### Periodo revisado: {inferir del contexto}

{Si hay seccion AVANCES del researcher:}
### Lo que se avanzo
{para cada item: "- {item}"}

{Si hay seccion TRABADOS del researcher:}
### En lo que estamos trabados
{para cada item: "- {item} — Bloqueante: {bloqueante} ({dias}d)"}

{Si hay seccion PROXIMO del researcher:}
### Lo que se viene
{para cada item: "- {item}"}

---

{Si hay seccion DISCUSIONES del researcher:}
### Discusiones del periodo
{para cada item: "- [{fuente}] {de}: {resumen}"}

{Si hay seccion TEMAS KB del researcher:}
### Temas pendientes en KB
{para cada item: "- [{tipo}] {texto} ({antiguedad}d)"}

{Si hay seccion CONTEXTO PARTICIPANTES del researcher:}
### Contexto de participantes
{para cada item: "**{persona}** ({rol}) — Issues: {issues} | Compromisos: {compromisos}"}

---

{Si hay seccion HORIZONTE del researcher:}
### Horizonte estrategico
{para cada item: "- {program/research}: {details}"}

---

### Agenda sugerida
{para cada item del synthesizer: "{seq}. [{prioridad}] {tema} — {por_que}"}

### Preguntas recomendadas
{para cada item del synthesizer: "- {pregunta}"}
```

Reglas de formateo:
- Omitir secciones enteras si el agente correspondiente no las devolvio
- Compromisos incumplidos siempre en bold como prioridad alta
- Si algun agente devuelve formato inesperado, mostrar su output raw como fallback

### Paso 5: Gate de seguimiento

AskUserQuestion:
- Pregunta: "Quieres hacer algo mas?"
- Opciones:
  - `[G]` Guardar prep como borrador en KB (via `kb meeting create` directo)
  - `[X]` Listo

Si elige `[G]`: persistir via `"$KB_CLI" meeting create` con los datos del prep (fecha, participantes, temas, agenda sugerida).

### Paso 6: Propagacion de completitud

Despues de guardar el prep (o incluso si el usuario no guarda pero el prep se genero):

1. Consultar acciones pendientes: `"$KB_CLI" todo list --pending`
2. Buscar acciones que referencien la reunion preparada:
   - Por nombre de persona (asistentes del evento)
   - Por tema (keywords del titulo del evento)
   - Ejemplos: "Preparar reunion con X", "Revisar contexto de Y"
3. Si encuentra matches, ofrecer marcar como completadas (mismo patron que /kb:comentarios Fase 4)

---

## Modo REVISAR — Revisar notas y docs de reuniones pasadas

Keyword = todo lo que siga a `revisar ` o `review ` en `$ARGUMENTS`.

### Paso 1: Buscar eventos

Use the active **workspace provider** to search calendar events for `"{keyword}"` looking back 30 days.

Mostrar resultados como tabla. Si no hay resultados: "No se encontraron eventos con '{keyword}' en los ultimos 30 dias."

Si hay varios, preguntar cual revisar. Si hay uno solo, usarlo directamente.

### Paso 2: Obtener detalle y docs adjuntos

Use the active **workspace provider** to show the full event detail for `{event_id}`.

Extraer adjuntos (Google Docs). Para cada adjunto:
Use the active **workspace provider** to read the document tabs for `{file_id}`.

### Paso 3: Presentar resumen estructurado

```
## Revision: {titulo del evento}

**Fecha:** {fecha} | **Asistentes:** {nombres}

### Documentos adjuntos
{Para cada doc: titulo + contenido resumido}

### Decisiones detectadas
{Extraer decisiones del contenido}

### Acciones detectadas
{Extraer action items del contenido}

### Preguntas abiertas
{Extraer preguntas sin resolver}
```

### Paso 4: Gate de seguimiento

AskUserQuestion:
- Pregunta: "Que quieres hacer con esta informacion?"
- Opciones:
  - `[G]` Guardar en KB (pipeline: meeting-parser → gate → meeting-persister)
  - `[A]` Crear acciones detectadas (con dedup via `--force` si necesario)
  - `[X]` Listo

Si elige `[G]`:
1. Lanzar `meeting-parser` con el texto y metadata extraidos → retorna PARSED_MEETINGS
2. Presentar al usuario un resumen de lo que se va a persistir (meetings, decisions, actions, questions). Gate via AskUserQuestion: aprobar / editar / cancelar.
3. Si aprobado → lanzar `meeting-persister` con los datos aprobados
4. Si hay senales de oportunidad en el output del persister → ofrecer crear programs exploratorios

Si elige `[A]`: para cada accion detectada, verificar con `"$KB_CLI" todo find "{keyword}"` antes de crear. Usar `--force` solo si el usuario confirma.

---

## Modo SYNC — Sincronizar reuniones pasadas

Pipeline de 3 agentes orquestado por este skill:

### Paso 1: Descubrir eventos

```
Agent tool:
  subagent_type: "calendar-discoverer"
  prompt: "TIME_WINDOW: ultimos 14 dias"
```

Retorna CALENDAR_EVENTS con lista de eventos + contenido crudo.

Si no hay eventos nuevos → reportar "Sin reuniones nuevas para sincronizar" y terminar.

### Paso 2: Parsear contenido

Para cada evento nuevo con contenido:
```
Agent tool:
  subagent_type: "meeting-parser"
  prompt: "TEXTO: {contenido del evento}
  METADATA:
    titulo: {titulo}
    fecha: {fecha}
    canal: calendar
    attendees: [{attendees}]
    modulo: {modulo si conocido}
  EVENT_ID: {event_id}"
```

Retorna PARSED_MEETINGS con datos estructurados.

### Paso 3: Gate de aprobacion

Presentar resumen al usuario via AskUserQuestion:
- "{N} reuniones encontradas, {M} decisiones, {P} acciones, {Q} preguntas"
- Opciones: "Persistir todo (Recommended)" / "Revisar item por item" / "Cancelar"

Si elige revisar: mostrar cada meeting con sus decisions/actions y permitir editar/skip.

### Paso 4: Persistir

```
Agent tool:
  subagent_type: "meeting-persister"
  prompt: "PARSED_MEETINGS: {datos aprobados}
  DOC_REGISTRATION: {doc_id, doc_url, titulo — si hay docs adjuntos}"
```

Mostrar resumen del output (meetings creados, tasks creados, etc.).

Si hay senales de oportunidad → ofrecer crear programs exploratorios.

---

## Reglas generales

1. **Fechas**: siempre mostrar en formato legible (ej: "Lunes 9 de marzo, 10:00–11:00"), no ISO crudo
2. **Asistentes**: mostrar nombres o emails — preferir nombre si esta disponible
3. **Gates**: siempre con AskUserQuestion antes de persistir
4. **El skill orquesta, los agentes ejecutan**: calendar-discoverer descubre, meeting-parser interpreta, meeting-persister escribe. Las gates son del skill.
5. **Todo en espanol**: labels, mensajes, output
6. **Regla de opciones**: en cada punto de decision, presentar 2-4 opciones numeradas con recomendacion marcada + opcion abierta ("Otra cosa"). No hacer preguntas abiertas sin opciones (ver CLAUDE.md)
