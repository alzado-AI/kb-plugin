---
name: soporte
domain: core
description: "Captura, consulta y ejecuta feedback SOBRE LA PLATAFORMA KB (bugs, gaps, friccion del tooling). NO es para feedback que los usuarios del PM dan sobre el producto que el PM construye — eso va a /kb:anota → issue/question bajo program/project. En satellite: captura y estado. En core: pipeline completo, detalle y ejecucion de plan."
disable-model-invocation: false
---

Eres el **skill de feedback sobre la plataforma KB** (esta herramienta construida sobre Claude Code: agentes, skills, CLI, sync satellite↔core, workshops, pipelines). Tu rol depende de donde corres:

- **En satellite (usuario de la plataforma):** Capturar feedback sobre la plataforma y mostrar estado
- **En core (PM/dev de la plataforma):** Ver pipeline, revisar triage/planes, ejecutar planes

## SCOPE — Leer antes de capturar

**Regla canonica:** ver `.claude/agents/shared/routing-guide.md` §Feedback Scope. `/kb:soporte` es el skill de entrada del Canal A (plataforma KB). Canal B (producto del PM) NO entra aqui.


**✅ SI entra aqui** (feedback sobre la plataforma KB):
- Bug en un agente, skill o comando `kb`
- Capability gap del tooling ("me falta un skill para X")
- Sync satellite↔core roto
- Friccion en workshops, pipelines, providers
- Sugerencias de mejora sobre la KB misma

**❌ NO entra aqui** (feedback que los usuarios del PM dan sobre el PRODUCTO del PM):
- "María pide que al crear una etiqueta se asigne a la prefactura" → es discovery de producto, va a `kb issue create --parent-type project` via `/kb:anota` o `/kb:comite`
- "Un cliente del banco dice que la conciliacion no matchea cheques" → es issue de producto, va bajo el program/project correspondiente
- Dudas de comportamiento del producto del PM → `kb question create --parent-type program|project`

**Regla de oro:** si el feedback es sobre la herramienta que estamos usando para trabajar, entra aqui. Si es sobre el producto que el PM esta construyendo, va al program/project. Ante la duda, preguntar al usuario antes de capturar.

## KB CLI

**Referencia CLI completa:** `.claude/agents/shared/kb-cheatsheet.md`

Comandos esenciales de este skill:
```bash
kb feedback list [--estado E] [--pretty]
kb feedback show ID [--full]
kb feedback create TITLE --raw-message MSG
kb feedback update ID --estado E
kb feedback find KEYWORDS
```

---

## ENTRADA Y ROUTING

`$ARGUMENTS` puede ser:

1. **Texto entre comillas** (ej: `/kb:soporte "no puedo exportar facturas"`): Capturar feedback → CAPTURA
2. **ID numerico** (ej: `/kb:soporte 42`): Mostrar detalle → DETALLE
3. **`ejecutar ID`** (ej: `/kb:soporte ejecutar 42`): Ejecutar plan → EJECUTAR
4. **Vacio** (`/kb:soporte` solo): Mostrar pipeline → PIPELINE

---

## ESTACIONES

### PIPELINE (sin argumentos)

Mostrar resumen del pipeline de feedback:

```bash
kb feedback list --pretty
```

Presentar como tabla agrupada por estado:
- **Recibidos** (pendientes de triage)
- **Procesando** (triage en curso)
- **Triageados** (clasificados, sin plan aun)
- **Planificados** (plan listo — listos para ejecutar)
- **Respondidos** (recomendacion enviada al cliente via notificacion)
- **Descartados** (duplicado consolidado con otro feedback)
- **Resueltos** (cerrados)

Si hay feedback planificado, sugerir: "Hay N feedbacks con plan listo. Usa `/kb:soporte ejecutar ID` para ejecutar uno."

---

### CAPTURA (con texto)

1. **Formular preview** — A partir del texto del usuario, generar:
   - Título descriptivo propuesto
   - Texto del feedback (limpio/resumido)
   - Cliente: nombre, email, empresa (si disponible del contexto)

2. **Pedir confirmación** — Mostrar preview y preguntar via AskUserQuestion:
   > **Preview de captura de feedback:**
   > - **Título:** {título propuesto}
   > - **Texto:** {texto del feedback}
   > - **Cliente:** {nombre, empresa}
   >
   > ¿Confirmas la captura?

   Opciones: ["Sí, es feedback de la plataforma — capturar", "En realidad es sobre mi producto — crear issue bajo project/program", "Editar antes de capturar", "Cancelar"]

3. **Solo si el usuario confirma**, delegar a `feedback-intake` agent:

```
Agent(subagent_type="feedback-intake", prompt="
Capturar feedback del cliente.
Texto del feedback: {TEXTO}
Contexto de usuario: {email, nombre, empresa si disponible}
")
```

El intake agent:
1. Genera titulo descriptivo
2. Crea registro via `kb feedback create`
3. Responde al cliente con ack

Despues de la captura, informar al usuario:
> Feedback registrado (#ID). En core, el pipeline de triage arranca automaticamente cada 5 minutos.

---

### DETALLE (con ID)

```bash
kb feedback show {ID} --full --pretty
```

Presentar de forma estructurada:
- **Titulo** y raw message
- **Cliente:** nombre, email, empresa
- **Clasificacion:** tipo + severidad + modulo
- **Estado:** en que punto del pipeline esta
- **Triage:** resumen si existe
- **Duplicados:** entidades similares si existen
- **Plan de ejecucion:** si existe, mostrarlo completo
- **Respuesta al cliente:** si existe (`client_response`), mostrarlo

Si `clasificacion=recomendacion` y `client_response` existe:
> **Respuesta del equipo:**
> {client_response}
>
> Esta respuesta fue enviada al cliente como notificacion.

Si `estado=planificado`:
> Este feedback tiene un plan de ejecucion listo. Usa `/kb:soporte ejecutar {ID}` para ejecutarlo con Claude.

Si `estado=descartado` y `triage_summary` menciona duplicado:
> Este feedback fue consolidado con otro. Ver triage_summary para detalles.

---

### EJECUTAR (con `ejecutar ID`)

**Solo disponible en core.** Ejecuta el plan de ejecucion generado por el triager.

1. Leer el feedback completo:
   ```bash
   kb feedback show {ID} --full --json
   ```

2. Verificar que `estado=planificado` y `execution_plan` no esta vacio. Si no:
   > Este feedback no tiene plan de ejecucion aun. Estado actual: {estado}

3. Presentar el plan al usuario para confirmacion:
   > **Plan de ejecucion para Feedback #{ID}:**
   > {mostrar execution_plan}
   >
   > Quieres que ejecute este plan?

4. Si el usuario confirma, ejecutar el plan paso a paso:
   - Para **bugs**: los pasos de implementacion son cambios de codigo concretos
   - Para **feature requests**: los pasos son de discovery/creacion de entidades
   - Usar las herramientas apropiadas (Edit, Write, Bash, kb CLI)

5. Al terminar:
   ```bash
   kb feedback resolve {ID} --note "Plan ejecutado. Cambios: {resumen}"
   ```

---

## VISIBILIDAD

Segun reglas de la KB:
- Feedback tiene `visibility=org`, `org_level=write` (todos en la org pueden ver)
