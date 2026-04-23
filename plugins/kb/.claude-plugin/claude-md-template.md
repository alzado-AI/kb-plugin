# KB Platform — Reglas transversales

Agregá este contenido a tu `~/.claude/CLAUDE.md` (o al CLAUDE.md del proyecto) para que Claude opere con las convenciones de la plataforma KB.

---

## Persistencia absoluta — todo va a la KB

Si la información tiene valor, va a la KB. No hay otro lugar válido. Nunca guardar info relevante en memoria local, variables de sesión, archivos temporales, ni "contexto mental". La KB (via CLI `kb` o skills `/kb:*`) es el único almacén que persiste, sincroniza y es consultable por otros agentes.

## KB primero — buscar antes de actuar

Primera acción ante cualquier solicitud que pueda existir en la KB: `kb search "<keyword>"` sin `--type` (full-KB scan). Solo si la KB devuelve vacío, o si lo buscado es inherentemente externo (último email, evento de calendario, PR en GitHub), ir al provider — comunicando "busqué en KB, no hay → voy a <provider>". Ir directo al provider sin pasar por KB rompe la regla.

## KB primero, provider después

La KB es el sistema de registro. Los providers (Linear, Google Workspace, Intercom, etc.) son interfaces externas. Toda información se escribe primero en KB y luego se sincroniza al provider — nunca al revés. Flujo correcto: `kb issue create` → `kb linear issue create`. Flujo incorrecto: `kb linear issue create` sin `kb issue create`.

## Invocación proactiva de skills

Cuando la intención del usuario mapea a un skill existente, invocar ese skill **antes** de responder ad-hoc. Aplica aunque el usuario no use la barra `/`. Tabla rápida:

| Intención | Skill |
|---|---|
| "trabajar en un program", "explorar oportunidad", "hagamos discovery" | `/kb:program` |
| "ejecutar project", "implementar X", "trabajemos esta solución" | `/kb:project` |
| "buscar información sobre X" | `/kb:busca` |
| "qué tengo pendiente" | `/kb:pendientes` |
| "qué tengo hoy/esta semana", "prepará reunión X" | `/kb:calendario` |
| "analiza este problema", "challengeá esto" | `/kb:analiza` |
| "investigá competidor/empresa X" | `/kb:investiga` |
| "generá memo/brief/comunicado" | `/kb:memo` |
| "generá presentación de X" | `/kb:presentacion` |
| "generá reporte/archivo (xlsx/pdf/csv) de X" | `/kb:reporte` |
| "crea dashboard de X" | `/kb:bi` |
| "arreglá issue X" | `/kb:batman` |
| "refiná issue X" | `/kb:refinar` |
| "cómo va cobranza / metas" | `/kb:cobranza` o `/kb:metas` |
| "vista 360 del cliente X" | `/kb:clientes` |
| "anotá esto" | `/kb:anota` |
| "bug en el agente/skill/CLI" | `/kb:soporte` |

Ante ambigüedad, invocar el skill más amplio.

## Templates obligatorios

Todo archivo que se genera pasa por un template, sin excepción. Si no existe uno aplicable, se crea antes de generar (`kb template create`). Flujo:
1. `kb template list --tipo <tipo>` + `kb search <keyword> --type template`
2. Si hay match, usarlo. Si hay varios, preguntar. Si no hay, crear el template con el usuario antes de generar.
3. Leer instrucciones con `kb template show <slug> --pretty`, o `--read-base-file` para templates binarios/híbridos.
4. Bajar el template, rellenar, subir con `kb doc upload`.

## Persistencia proactiva de documentos

Cuando aparezca un link de doc externo (Google Docs/Sheets/Drive) o un archivo subido, **la primera acción** es registrarlo en KB antes de leer contenido:
- `kb doc register "<nombre>" "<url>" --tipo <tipo>` para links externos
- `kb doc upload <path>` para archivos locales

Ambos auto-linkean a la sesión activa. El doc aparece inmediatamente en el panel de archivos del workshop.

## Archivos generados

Cuando generes un archivo descargable: (1) escribir en `/tmp/`, (2) `kb doc upload` para persistirlo y auto-linkearlo a la sesión, (3) leer `public_view_url`/`public_download_url` del JSON y compartirlo con el usuario.

## Challenger

Challengeá siempre antes de aceptar un problema:
1. **Solucionitis** — separar dolor de solución propuesta
2. **Evidencia** — datos, frecuencia, issues. Sin evidencia = más escrutinio
3. **Duplicidad** — ya existe program/project similar?
4. **Raíz vs síntoma** — es el problema raíz?

Tono: coach que ayuda a pensar. Si el problema es claro con evidencia, avanzar rápido.

## Stakeholders y personas

Al crear/completar trabajo, registrar stakeholders (roles: `solicitante`, `destinatario`, `reportero`, `interesado`). Si una persona o módulo no está en DB, crearlo via `kb person create --upsert` sin interrumpir el flujo.

## Visibilidad autónoma

Aplicar sin preguntar según categoría:
- **Contenido de la org** (Program, Project, Issue, Opportunity, etc.): `org` + `write`
- **Referencia/auditoría** (Learning, Meeting, Pipeline): `org` + `read`
- **Trabajo personal** (Conversation, Notification, Pipeline Run, ToDo sin stakeholders): `private`
- **Info sensible** (financiera personal, salarios, feedback de performance): preguntar antes

## Lectura multi-usuario

Sistema multi-usuario. Al listar items, separar "tus items" (`created_by == mi_uuid`) de "items de la org" (`visibility == org`). Mi UUID: `kb auth status`.
