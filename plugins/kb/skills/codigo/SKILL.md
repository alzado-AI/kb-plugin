---
name: codigo
domain: pm
description: "Navegar y explorar el codebase del producto (repos GitHub). Responde preguntas sobre features, arquitectura, modelos de datos y flujos. Acepta repo o tema: /kb:codigo invoice-service, /kb:codigo como funciona la conciliacion."
disable-model-invocation: false
---

El usuario quiere explorar o entender algo del codebase del producto. La organizacion de GitHub se lee de `"$KB_CLI" team list` + `"$KB_CLI" person list` o se infiere del contexto del repositorio.

**Cruzar codigo con reglas del dominio.** Si el usuario pregunta "como funciona X" donde X es un concepto del negocio (ej: "como funciona la conciliacion"), cargar `kb org-context --query "X" --format prompt` antes de invocar al codebase-navigator. Pasar el contexto al sub-agente para que su explicacion **conecte el codigo con las reglas/terminos del dominio**: ej. "el codigo aplica `[rule:romana-vs-ingreso]` en `services/peso.py:42`". Esto convierte la respuesta de "que hace el codigo" en "que hace el codigo Y por que lo hace asi segun el negocio".

## Paso 1: Obtener datos

Usa el agente `codebase-navigator` (Agent tool, subagent_type="codebase-navigator") para realizar la exploracion.

Si el usuario incluyo el tema junto al comando (ej: `/kb:codigo invoice-service`, `/kb:codigo como funciona la conciliacion bancaria`, `/kb:codigo quiero replicar el modelo de facturas`), lanza el agente directamente con $ARGUMENTS como query de exploracion.

Si no incluyo detalle, pregunta brevemente que quiere explorar del codebase.

El agente devuelve datos estructurados (secciones `=== META ===`, `=== RESUMEN FUNCIONAL ===`, etc.), NO output formateado.

## Paso 2: Formatear output

Tomar las secciones del output del agente y formatear en markdown legible:

```
## {query de META}
Repos: {repos de META}

### Resumen funcional
{texto de RESUMEN FUNCIONAL}

### Flujos
{para cada item en FLUJOS: "- **{flujo}**: {endpoint} — Datos: {datos}"}

### Modelo de datos
{para cada item en MODELO DATOS: "- **{entidad}**: {campos} — Relaciones: {relaciones}"}

### Funcionalidad existente
| Funcionalidad | Repo | Estado | Reutilizable? |
|---------------|------|--------|---------------|
{para cada item en FUNCIONALIDAD EXISTENTE: "| {funcionalidad} | {repo} | {estado} | {reutilizable} |"}

### Gaps
{para cada item en GAPS: "- **{gap}**: {implicacion}"}

### Archivos clave
| Archivo | Repo | Relevancia |
|---------|------|-----------|
{para cada item en ARCHIVOS CLAVE: "| {archivo} | {repo} | {relevancia} |"}
```

Reglas de formateo:
- Omitir secciones vacias
- Si el agente devuelve secciones inesperadas o formato raro, mostrar el output raw del agente como fallback

## Paso 3: Post-resultado

Segun el contexto de la pregunta:
- **Exploracion general**: Pregunta al usuario si quiere persistir los hallazgos en la base de conocimiento. Si dice que si, usa `"$KB_CLI" learning create` directamente.
- **Para prototipo**: Sugiere usar `/kb:project` (estacion PROTOTIPO) con los datos extraidos. Ejemplo: "Puedo usar `/kb:project` para integrar este modelo de datos en el producto real. Quieres?"
- **Para discovery**: El output ya esta estructurado para integrarse al documento de discovery. No preguntar si guardar — el facilitador de discovery se encarga de la persistencia.
