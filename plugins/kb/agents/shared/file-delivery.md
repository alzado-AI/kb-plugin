# Entrega de archivo (OBLIGATORIO)

Toda corrida que produzca datos DEBE entregar al usuario un archivo descargable, ademas del resumen en texto. Devolver solo texto cuenta como bug.

1. **Determinar formato:** preguntar al usuario que formato quiere (`xlsx`, `csv`, `pdf`, `html`, `json`) si no lo especifico al invocar. NO asumir un default — el formato es decision del usuario, no del agente. Si se invoco desde un skill que pasa template, leer `output_format` del template.

2. **Generar archivo a `${ARTIFACT_DIR:-/tmp}/{filename}.{ext}`** con el contenido especifico del reporte del agente (ver bloque "Formatos" de cada agente para detalles del layout por extension).

3. **Subir via KB + entregar al usuario** → ver `.claude/agents/shared/report-upload-protocol.md` (upload bare o con `--parent-type`/`--parent-id` si el caller los aporto; mensaje final; manejo de errores).
