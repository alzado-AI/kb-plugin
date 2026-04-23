# Doc-First — Protocolo compartido

El documento externo (Google Doc) es la fuente de verdad para contenido. La KB almacena metadata y la referencia al documento, NO el contenido.

## Cuando aplica

Este protocolo aplica a todo agente que escriba contenido destinado a un documento externo (discovery, memos, reportes persistentes). NO aplica a contenido tecnico que queda exclusivamente en KB (ej: `tecnica` de programs/projects).

## A. Resolucion del documento

1. Buscar doc existente: `kb doc list --parent-type {type} --parent-slug {slug} --tipo pdd`
2. Si existe → extraer doc_id de la URL, modo **ACTUALIZAR**
3. Si no existe → `kb google doc ensure --title "{titulo}" --folder-id {folder}` → registrar con `kb doc register`
4. Si el caller ya pasa DOC_ID → usarlo directo

**Regla:** el doc_id se obtiene de la URL de Google Docs (entre `/d/` y `/edit`).

## B. Lectura del documento

**SIEMPRE leer antes de escribir.** El doc tiene la version mas reciente — puede incluir ediciones de usuarios.

```bash
# Estructura de tabs con IDs
kb google doc list-tabs DOC_ID

# Contenido estructurado con secciones, tablas, indices
kb google doc read-structured DOC_ID [TAB_IDs...]
```

`read-structured` retorna JSON con:
- `title`: nombre del tab
- `preamble`: elementos antes del primer heading
- `sections[]`: heading, level, start_index, end_index, elements[]
  - Cada element tiene: type (paragraph|table|heading), text/header/rows, index

Usar esta estructura para entender que hay en el doc antes de escribir.

## C. Niveles de escritura

Elegir el nivel apropiado segun la operacion. De mas grueso a mas fino:

| Nivel | Comando | Cuando usar |
|-------|---------|-------------|
| **Tab completo** | `kb google doc upsert-tab DOC_ID --tab-id T --content-markdown-file F` | Escritura inicial, reescritura mayor |
| **Seccion** | `kb google doc update-tab DOC_ID TAB_ID --content-markdown-file F --strategy sections` | Actualizar una o mas secciones H1 |
| **Insertar (despues)** | `kb google doc insert-blocks DOC_ID TAB_ID --after-heading "H" --content-markdown-file F` | Agregar contenido al inicio de una seccion (despues del heading) |
| **Insertar (antes)** | `kb google doc insert-blocks DOC_ID TAB_ID --before-heading "H" --content-markdown-file F` | Insertar ANTES de un heading (al final de la seccion anterior). Operacion segura que no rompe anclas de comentarios |
| **Celda** | `kb google doc edit-cell DOC_ID TAB_ID --table-index N --row R --col C --text "X"` | Corregir un dato en una tabla |
| **Texto** | `kb google doc replace-text DOC_ID TAB_ID --find "viejo" --replace "nuevo" --section "H"` | Corregir un texto puntual |
| **Eliminar** | `kb google doc delete-section DOC_ID TAB_ID --heading "H"` | Quitar una seccion obsoleta |

**`--strategy sections` es el default** para `update-tab` — solo reemplaza secciones H1 que el agente envia. Lo demas queda intacto. NUNCA usar `--strategy full` a menos que se quiera borrar todo.

**Siempre usar `--content-markdown-file`** para escritura de contenido. Markdown produce formato nativo de Google Docs — tablas nativas, headings con estilo, bullets, etc.

**`--section` en edit-cell y replace-text** es opcional — acota la busqueda a una seccion por heading. Sin el flag, busca en todo el tab.

## D. Preview antes de escribir

Para **ediciones quirurgicas** (niveles celda, texto, eliminar), el agente DEBE mostrar al usuario que va a cambiar antes de ejecutar:

```
Quiero hacer este cambio en el tab "Negocio":
- Celda [fila 2, col 1]: "15%" → "22%"
¿Procedo?
```

Para **escritura inicial** de tabs/secciones completas, escribir directo. El usuario puede revertir via historial de Google Docs.

## D2. Proteccion de anclajes de comentarios

**Cualquier operacion que elimine o reemplace texto existente destruye silenciosamente los anclajes de comentarios.** Los comentarios quedan huerfanos: siguen visibles en el panel pero ya no estan atados a ninguna posicion del documento. Esto es irreversible.

**Operaciones destructivas para anclajes:**

| Operacion | Impacto |
|-----------|---------|
| `delete-section` | Destruye anclajes de todos los comentarios en esa seccion |
| `update-tab --strategy full` | Destruye TODOS los anclajes del tab |
| `update-tab --strategy sections` | Destruye anclajes de las secciones reemplazadas |
| `replace-text` | Destruye el anclaje del texto reemplazado |
| `edit-cell` | Destruye el anclaje si habia comentario sobre esa celda |

**Protocolo obligatorio antes de cualquiera de estas operaciones:**

1. Correr `kb google doc comments DOC_ID --with-context`
2. Si hay comentarios en el contenido afectado → mostrar advertencia al usuario con la lista de comentarios solapantes
3. Esperar confirmacion explicita del usuario antes de ejecutar
4. Si no confirma → cancelar y reportar

**insert-blocks** es la unica operacion de escritura que no destruye anclajes existentes — inserta sin tocar lo que ya esta.

## E. Formato markdown

Los agentes deben escribir contenido como markdown a archivos en `/tmp/` y pasarlos via `--content-markdown-file`. El backend Google handler convierte markdown a formato nativo de Google Docs:

- `# Heading` → Heading 1, `## Heading` → Heading 2, etc.
- `**bold**`, `*italic*`, `` `code` ``, `[link](url)` → formato inline
- `- item` → bullet list
- `1. item` → numbered list
- Tablas markdown → tablas nativas de Google Docs:
  ```markdown
  | Feature | IN | OUT | Notas |
  |---------|-----|------|-------|
  | Conciliacion | ✅ | | Solo bancos |
  ```
  Limitacion: celdas son texto plano (sin bold/italic dentro de celdas). Para editar celdas especificas post-creacion: `kb google doc edit-cell`.

**Workflow:**
1. `Write(/tmp/{slug}-{tipo}.md, contenido markdown)` — via herramienta Write
2. `kb google doc update-tab DOC_ID TAB_ID --content-markdown-file /tmp/{slug}-{tipo}.md --strategy sections`

**En tabs_json** (para `kb google doc create`): usar campo `content_markdown`:
```json
{"title": "Tab Name", "emoji": "🥇", "content_markdown": "# Heading\n\nContenido...\n"}
```

## F. Registro en KB

Despues de crear un doc nuevo:
```bash
kb doc register "{nombre}" "{url}" --tipo pdd --parent-type {type} --parent-slug {slug}
```

La KB almacena la referencia (URL, parent, tipo), NO el contenido. El contenido vive en el doc.

## G. Comentarios

Para leer comentarios con contexto (seccion, texto citado):
```bash
kb google doc comments DOC_ID --with-context
```

Retorna `tab_id`, `tab_title`, `section` (heading) y `quoted` (texto citado) por cada comentario. Util para que el agente entienda que le estan pidiendo y donde.
