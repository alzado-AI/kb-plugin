# Protocolo de Entrada de Workshops

Shared entre `/kb:program` y `/kb:project`. Al entrar al workshop — en CUALQUIER estacion — ejecutar SIEMPRE estos 2 pasos.

## Paso 1: Leer template

```bash
kb template show program-discovery --read-base-file
```

Guardar como `TEMPLATE`. El flag `--read-base-file` es **OBLIGATORIO** — incluye `base_file_content` con el scaffold completo (tabs, project_tabs, rules, content_scaffold por tab, metodologia declarada). Sin ese flag, `kb template show` devuelve solo el body.

**Si el workshop es `/kb:project`:** leer la seccion `project_tabs` de `base_file_content` como `PROJECT_TEMPLATE` — contiene tabs, `content_scaffold` por tab y metodologia declarada para projects.

**NUNCA improvisar deliverables ni estructura** — el scaffold del template es la unica fuente de verdad. Si `base_file_content` es `null`, reportar el problema en vez de generar contenido inventado.

## Paso 2: Leer estado del doc

```bash
kb doc list --parent-type program --parent-slug {PROGRAM_SLUG} --tipo pdd
```

- Si existe → extraer `doc_id` y luego `kb google doc list-tabs DOC_ID`. Guardar como `DOC_STATE`.
  - Para `/kb:project`: filtrar tabs de ESTE project → `DOC_STATE`.
- Si no existe doc → en `/kb:program` se crea en SETUP INICIAL; en `/kb:project`, no se puede escribir contenido sin doc del program.

**Sin `TEMPLATE` (o `PROJECT_TEMPLATE`) y `DOC_STATE` en contexto, el skill no puede orquestar correctamente.**
