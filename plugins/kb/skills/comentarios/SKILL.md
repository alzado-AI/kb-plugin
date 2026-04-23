---
name: comentarios
domain: core
description: "Leer y analizar comentarios de cualquier documento del workspace provider. Acepta URL, doc_id o nombre: /comentarios memo-cheques."
disable-model-invocation: false
---

el usuario quiere ver los comentarios de un documento del workspace. Este skill lee comentarios via el workspace provider (operacion `doc-comments` — resolver comando desde `tools/*/provider.md`), los presenta organizados, y opcionalmente los cruza con un discovery para proponer actualizaciones.

## REGLA — registrar antes de leer

Si el usuario pasa una **URL del doc** (no un slug ni doc_id), la primera accion debe ser registrar el doc en KB para que aparezca en el panel del workshop:

```bash
"$KB_CLI" doc register "<nombre-inferido>" "<url>" --tipo <tipo>
```

(Auto-linkea a la sesion activa via `document_session_links`, sin pisar el parent canonico. Si el doc ya esta en KB, saltar.)

## Fase 1 — Identificar documento

Parsear `$ARGUMENTS` para obtener el `doc_id`:

1. **URL de documento** — Si el argumento contiene una URL de documento (ej: `docs.google.com/document/d/`), extraer el ID.
2. **doc_id directo** — Si es un string alfanumerico largo (>20 chars, sin espacios), usarlo directamente.
3. **Nombre corto** — Si es un nombre como `pdd-cheques`, `memo-capacitacion`, etc.:
   a. Buscar en DB via `kb doc list` para encontrar doc_id por nombre.
   b. Si no hay match en DB, usar el workspace provider (operacion `search-drive` — resolver comando desde `tools/*/provider.md`) para buscar por nombre.
4. **Sin argumentos** — Llamar `kb google doc comments-inbox --days 14` para descubrir docs con comentarios pendientes en las ultimas 2 semanas, presentar la lista al usuario y pedir cual quiere revisar.

## Fase 2 — Leer y presentar comentarios

1. Llamar al workspace provider, operacion `doc-comments` (resolver comando desde `tools/*/provider.md`).
2. Presentar los resultados al usuario organizados:
   - **Comentarios abiertos** primero, con detalle completo (texto citado, contenido, replies, autor, fecha)
   - **Comentarios resueltos** despues, en formato compacto
3. Incluir un resumen al inicio: total, abiertos, resueltos, autores principales.

## Fase 3 — Cruce con discovery (opcional)

Despues de presentar los comentarios, preguntar:

> "Quieres que cruce estos comentarios con un discovery para proponer actualizaciones?"

Si el usuario dice que si:

1. **Inferir discovery:** Del nombre del documento (ej: `memo-cheques` -> program `medios-de-pago`, project `cheques`). Verificar via `kb program list` + `kb project list`. Si no es obvio, preguntar.
2. **Leer discovery:** `kb program show SLUG --content-summary` o `kb project show SLUG --content-summary` primero. Luego leer via cache local unicamente las secciones que los comentarios referencian (lectura progresiva, no leer todo).
3. **Clasificar cada comentario abierto** en una de estas categorias:
   - `ACTUALIZAR_DISCOVERY` — El comentario sugiere un cambio concreto al discovery (scope, flujo, tecnologia, etc.)
   - `YA_RESUELTO` — Lo que pide el comentario ya esta en el discovery actual
   - `PREGUNTA_NUEVA` — El comentario plantea una pregunta que deberia ir a preguntas.md
   - `DECISION_NUEVA` — El comentario implica una decision de producto que debe documentarse
   - `NO_APLICA` — Comentario cosmetic/editorial que no afecta el discovery
4. **Presentar propuestas** al usuario en formato tabla:
   ```
   | # | Comentario (resumen) | Clasificacion | Seccion afectada | Propuesta |
   ```
5. **Si el usuario aprueba** las propuestas (todas o un subset):
   - Delegar a `doc-writer` (Agent tool, subagent_type="doc-writer") con DOC_ID, TAB_ID (del tab afectado), e INSTRUCCION con las secciones a actualizar y el contenido a agregar/modificar. Pasar las citas exactas de los comentarios. doc-writer usa Modo C (patch) para ediciones quirurgicas.
   - El writer se encarga de editar las secciones del discovery manteniendo formato y consistencia.

## Fase 3.5 — Acciones sobre comentarios (cerrar el loop)

Después de presentar los comentarios abiertos (Fase 2) y antes del cruce-con-discovery (Fase 3), ofrecer acciones directas:

> "¿Quieres actuar sobre algún comentario?"
> 1. Resolver (marcar como cerrado)
> 2. Responder
> 3. Ambas
> 4. No, solo revisar

**Resolver** — acepta IDs individuales o "todos los abiertos":

```bash
# Uno
kb google doc comment-resolve DOC_ID COMMENT_ID

# Batch (preferido para N > 1 — un solo round-trip, reporta fallos por ID)
kb google doc comments-resolve DOC_ID --ids ID1,ID2,ID3
```

El batch devuelve `{resolved_count, failed_count, resolved: [...], failed: [{comment_id, error}]}`. Reportar al usuario cuáles se resolvieron y cuáles fallaron.

**Responder** — para cada comentario aprobado, pedir el texto de la respuesta (o tomar del dictado del usuario):

```bash
kb google doc reply DOC_ID COMMENT_ID --content "texto de la respuesta"
```

Responder uno a la vez; no hay endpoint batch para replies (cada uno lleva contenido distinto).

**Regla de autorización:** nunca ejecutar resolver/responder sin confirmación explícita del usuario con los IDs o el filtro ("todos", "los de Fernanda", "del 1 al 5").

Tras ejecutar, pasar a Fase 3 (cruce con discovery) si el usuario quiere, o directo a Fase 4.

## Fase 4 — Presentar resumen estructurado

Despues de leer y analizar los comentarios, presentar al usuario un resumen estructurado directamente en el output (NO crear archivo):

```
Comentarios: {nombre del doc}
Fuente: {link del Google Doc}
Fecha lectura: {fecha}
Total: {N} ({abiertos} abiertos, {resueltos} resueltos)

Abiertos:
- {autor} ({fecha}): "{contenido}" — Quoted: "{texto citado}"

Resueltos (resumen):
- {autor}: "{contenido}" — resuelto {fecha}
```

Ordenar comentarios por posicion en el doc fuente. Agrupar por seccion cuando sea posible.

## Fase 5 — Propagacion de completitud

Despues de completar la tarea (leer comentarios, persistir, o cruzar con discovery):

1. Consultar acciones pendientes: `kb todo list --pending`
2. Buscar acciones que matcheen el documento revisado:
   - Buscar por nombre del documento, nombre del autor, o keyword clave
   - Ejemplos: "Revisar documento de Fernanda", "Dejar comentarios en memo-X"
3. Si encuentra matches, presentar al usuario:
   > "Detecte estas acciones relacionadas que podrian estar completadas:"
   > - [ ] {accion encontrada}
   > "¿Marco como completadas?"
4. Si el usuario confirma, ejecutar directamente:
   `kb todo complete {ID}` para cada tarea confirmada.

## Notas

- Puede resolver y responder comentarios cuando el usuario aprueba (Fase 3.5). La edición de contenido del discovery sigue vía `doc-writer` (Fase 3).
- Los comentarios resueltos se muestran para contexto pero no se cruzan con discovery (solo los abiertos).
- Si el doc no tiene comentarios, informar y terminar.
