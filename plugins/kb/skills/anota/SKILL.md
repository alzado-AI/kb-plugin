---
name: anota
domain: core
tier: basic
description: "Anotar información rápida en la base de conocimiento del producto. Clasifica el input y delega al sub-agente correcto para persistir la nota (acciones, preguntas, producto, equipo, etc.)."
disable-model-invocation: false
---

El usuario quiere anotar algo en su base de conocimiento.

## Patrones comunes

Clasificar el input por prefijo y delegar al sub-agente correcto:
- `oportunidad: {necesidad}` → usar `"$KB_CLI" program create` directamente
- `research: {pregunta}` → `"$KB_CLI" question create "{pregunta}" --category research` directamente
- `objective: {metrica}` → `"$KB_CLI" objective create` directamente
- `doc: {nombre} {link}` → usar `"$KB_CLI" doc register` directamente (tipo: otro por default)
- Notas de reunion / reunion data → pipeline: `meeting-parser` → gate → `meeting-persister`
- Sin prefijo → clasificacion automatica por contenido, ejecutar KB CLI directo

**Extraccion incremental de dominio:** Si el texto contiene una definicion explicita (patrones `"X es Y"`, `"X significa Y"`, `"X = Y"`, sigla seguida de explicacion entre parentesis, `"la sigla X"`) o una regla de interpretacion (`"si X entonces Y"`, `"siempre hay que X"`, `"nunca Y"`, `"excluir X"`, `"lo importante es"`), ofrecer al usuario via `AskUserQuestion` extraer el item como `Term` o `BusinessRule`:

- Delegar el chunk a `domain-extractor` (subagent_type="domain-extractor") con el texto relevante.
- Recibir JSON con `terms[]` y/o `rules[]`.
- Mostrar al usuario para validar, persistir via `kb term create` / `kb rule create`.
- NO correr `/empresa` entero — uno o pocos items a la vez.

Si el usuario no confirma, seguir el flujo normal de anotacion.

Routing por tipo de informacion:
1. **Tareas** → `"$KB_CLI" todo create` directo. **Preguntas** → `"$KB_CLI" question create` directo. **Aprendizajes** → delegar a `aprendizaje-writer`. **Personas/equipos** → `"$KB_CLI" person create --upsert` / `"$KB_CLI" team create` directo.
2. **Notas de reunion, asistentes, decisiones de reunion** → pipeline: lanzar `meeting-parser` (subagent_type="meeting-parser") con el texto y metadata → presentar resumen al usuario → si aprobado, lanzar `meeting-persister` (subagent_type="meeting-persister") con los datos estructurados
3. **Feedback / input sobre un producto o proceso** — distinguir DOS canales. **NO mezclar.** (Regla canonica: `.claude/agents/shared/routing-guide.md` §Feedback Scope.)
   - **(a) Feedback sobre la PLATAFORMA KB** (esta herramienta: agentes, skills, CLI `kb`, sync satellite↔core, workshops, pipelines, providers) → delegar a `feedback-intake` tras confirmacion. Ejemplos: "el agente X se colgo", "me falta un skill para Y", "`/comite` no lista los issues nuevos", "el sync no trajo el ultimo feedback".
   - **(b) Input de usuarios del PM sobre el PRODUCTO del PM** (el sistema que el PM construye: prefacturas, conciliacion, CxC, cheques, etc.) → NO va a `feedback-intake`. Crear directamente `"$KB_CLI" issue create ... --parent-type project|program` (si es un feature/bug concreto) o `"$KB_CLI" question create ... --parent-type project|program` (si es una duda de comportamiento). Ejemplos: "María pide que al crear etiqueta se asigne a la prefactura", "un cliente no puede exportar el estado de cuenta en PDF", "duda: cuando deja de aparecer una prefactura en el EECC".
   - Si el usuario confunde los canales o el input es ambiguo, presentar via AskUserQuestion: "¿Es feedback sobre la plataforma KB (la herramienta) o sobre el producto que estas construyendo?". Solo despues de aclarar, rutear.
4. **Programs nuevos** → usar `"$KB_CLI" program create` directamente
5. **Registrar documentos** → usar `"$KB_CLI" doc register` directamente
6. **SIEMPRE crear también una entrada de reunion** via `"$KB_CLI" meeting create` con el formato estándar (fecha, participantes inferidos, temas, decisiones, acciones). Tratar cada `/anota` como un log de reunión además de clasificar el contenido en los archivos temáticos correspondientes.

**Gate de confirmación para feedback de plataforma:** Antes de delegar a `feedback-intake`, siempre:
1. Confirmar que el feedback es sobre la plataforma KB (no sobre el producto del PM). Si hay duda, preguntar.
2. Mostrar preview del contenido a capturar.
3. Pedir confirmación explícita via AskUserQuestion con opciones: ["Sí, es feedback de la plataforma — capturar", "En realidad es sobre mi producto — crear issue bajo project/program", "Cancelar"]
4. Solo delegar a `feedback-intake` si elige la primera.

Si el usuario incluyó la nota junto al comando (ej: `/anota revisar reuniones mensuales con el equipo`), procesa directamente usando $ARGUMENTS como contenido.

Si no incluyó detalle, pregunta brevemente qué quiere anotar.

Prioriza velocidad: clasifica rápido, delega al sub-agente correcto, y confirma dónde quedó guardado.
