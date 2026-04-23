# Report upload protocol

Protocolo compartido para agentes que generan archivos reportables (xlsx, csv, pdf, html, json) y los entregan al usuario via la plataforma. Usado por `erp-reporter`, `financial-analyst`, `deal-analyzer` y cualquier otro agente cuyo output sea un archivo descargable.

## INPUT opcional que el caller puede aportar

Además del objetivo/template/params propios del agente, el caller puede pasar un parametro opcional para vincular el reporte a una entidad KB canonica:

- `parent_type` — tipo de entidad parent (`program`, `project`, `module`, `meeting`, etc.)
- `parent_id` — ID numerico de la entidad parent. Si el caller tiene un slug, debe resolverlo a ID antes de invocar al agente: `kb {entity} show SLUG | jq .id`.

Si estan presentes, el upload linkea el archivo al parent canonico. Si faltan, el upload sigue siendo bare (solo linkeado a la sesion activa).

## Pasos

1. **Escribir el archivo a `${ARTIFACT_DIR:-/tmp}/{filename}`** segun el formato elegido.

2. **Subir via KB:**
   ```bash
   # Forma basica (auto-linkea a la sesion activa)
   kb doc upload "$FILE"

   # Si el caller paso un parent canonico (INPUT → parent_type + parent_id):
   kb doc upload "$FILE" --parent-type "$parent_type" --parent-id "$parent_id"
   # El doc queda subido Y vinculado al Program/Project/etc como Document canonico.
   # NO pasar --parent-type workshop_session.
   ```

3. **Del JSON de respuesta extraer `public_download_url`** (y `public_view_url` si el formato es viewable: pdf, html, png, jpg, svg).

4. **Mensaje final al usuario:**
   > Reporte listo: [{nombre}]({public_download_url})
   > Tambien lo encontras en el panel de archivos.

5. **Errores:**
   - `kb doc upload` falla → mostrar error completo al usuario, NO continuar como si nada.
   - `CLAUDE_SESSION_ID` ausente → avisar modo local, dejar archivo en `/tmp/{nombre}` con instruccion clara.
   - `--parent-type`/`--parent-id` pasado pero el linkeo falla → el doc ya esta subido; reportar el error de vinculacion sin re-uploadear.

## Nota: clasificacion estructurada

Para reportes recurrentes con parametros tipados (ej: "reporte de cobranza por mes", "pipeline de ventas por Q"), usar el sistema de **Reports** (`kb report create ... --pipeline P`) en lugar de subir archivos ad-hoc. Cada ejecucion del pipeline produce un `ReportVariant` con params tipados y Documents linkados — sin necesidad de "clasificar" el archivo manualmente. Ver `kb report --help`.
