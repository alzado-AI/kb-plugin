# KB Plugin para Claude Code + Cowork

Plugin oficial de la plataforma Knowledge Base (KB). Entrega skills, sub-agentes y el CLI `kb` para trabajar contra un backend hosted, sin clonar repos ni correr infraestructura local.

## Qué trae el plugin

- **~80 skills** — workshops (`/kb:program`, `/kb:project`, `/kb:batman`), navegación (`/kb:pendientes`, `/kb:clientes`, `/kb:calendario`), generación (`/kb:memo`, `/kb:presentacion`, `/kb:reporte`), y más
- **~50 sub-agentes** — `doc-writer`, `meeting-parser`, `issue-writer`, `browser-navigator`, etc. Claude los invoca automáticamente según tarea
- El CLI `kb` vive en `cli/` de este mismo repo — se instala con `pip install git+https://...` (ver abajo)

## Instalación

### 1. Agregar el marketplace

En Claude Code o Cowork:
```
/plugin marketplace add alzado-AI/kb-plugin
```

### 2. Instalar el plugin

```
/plugin install kb
```

Claude Code copiará skills + agents a `~/.claude/plugins/cache/kb/`.

### 3. Instalar el CLI `kb`

Desde PyPI (ruta principal):
```bash
pip install alzadi-kb
```

Alternativa directa al repo (útil para pre-releases o pinear a un tag específico):
```bash
pip install "git+https://github.com/alzado-AI/kb-plugin.git@v0.1.3#subdirectory=cli"
```

Verificación: `kb --help` debe responder con los subcomandos (`auth`, `search`, `doc`, etc.).

Upgrade:
```bash
pip install --upgrade alzadi-kb
```

### 4. Autenticarte

```bash
kb auth login
```

Te imprime un código corto y abre `core.dominio.org/activate` en tu browser. Escribí ahí el **slug del tenant** que vas a usar (ej: `buk-finanzas`), hacé login, y confirmá el dispositivo. El CLI recibe tokens automáticamente.

### 5. (Recomendado) Copiar las reglas transversales

El plugin NO puede contribuir al CLAUDE.md de Claude Code — es un constraint del plugin system. Para que Claude entienda reglas globales como "KB primero antes de provider", "templates obligatorios para archivos generados", etc., copiá el template incluido:

```bash
cat ~/.claude/plugins/cache/kb/.claude-plugin/claude-md-template.md >> ~/.claude/CLAUDE.md
```

O al CLAUDE.md del proyecto donde trabajes.

## Uso

Después de los 5 pasos anteriores, abrí Claude Code o Cowork en cualquier directorio y:

- `/kb:program cheques receivables` — abre el workshop de exploración de una feature
- `/kb:trabajar` — escanea todas tus fuentes y prioriza pendientes
- `/kb:busca conciliacion` — busca el término cruzando KB + workspace providers
- "lee mi último email" — Claude invoca las tools del CLI automáticamente

## Multi-tenant

Si trabajás en varios tenants:

```bash
kb auth login                          # devuelve al browser, elegí otro slug
kb auth use <tenant>                   # switch de tenant activo
kb auth status                         # muestra el tenant activo + sesiones
kb auth list                           # lista tenants configurados
```

También podés pinnear una carpeta a un tenant con un archivo `.kb/context` en el directorio.

## Troubleshooting

- **`kb: command not found`** → correste `pip install kb-cli`? Agregá `~/.local/bin` al PATH si pip lo instaló ahí.
- **Skills no aparecen con prefix `/kb:`** → verificá `/plugin list` — el plugin debe estar enabled.
- **Auth falla en Cowork** → revisá que tengas conectividad HTTPS al backend. Cowork rutea por proxy automáticamente.

## Soporte

- Issues de la plataforma (bugs, gaps del tooling): usar `/kb:soporte` — va al pipeline de triage
- Documentación: https://core.dominio.org/docs
