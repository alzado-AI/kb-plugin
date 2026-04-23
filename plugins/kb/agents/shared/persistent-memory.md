# Estado Persistente de Agentes — Patron Canonico

Todo estado que un agente necesite recordar entre sesiones debe persistirse en KB via `kb context`.
NUNCA en archivos locales (`.claude/agent-memory/`, `/tmp/`, etc.) — esos se pierden al reiniciar el container
y no son propagables a satellites ni consultables cross-agent.

## Patron Canonico

```bash
# Leer estado
kb context show {clave} --section {agente} 2>/dev/null || echo "{}"

# Escribir/actualizar estado (JSON compacto en una linea)
kb context set {clave} '{...json...}' --section {agente}
```

**Seccion recomendada por agente:**

| Agente | Seccion | Claves tipicas |
|--------|---------|----------------|
| `external-searcher` | `external-searcher` | `watermarks`, `chat-spaces` |
| `codebase-navigator` | `codebase-navigator` | `repos`, `stack` |
| `code-publisher` | `code-publisher` | `pr-conventions`, `tracker-ids` |
| `code-implementer` | `code-implementer` | `repo-quirks`, `build-gotchas` |
| `code-reviewer` | `code-reviewer` | `state` |
| `issue-analyzer` | `issue-analyzer` | `repo-mapping`, `issue-patterns` |

## Que persiste en KB

- Resultados de descubrimiento reutilizables (tech stack, mapas de repos, convenciones)
- Estado de deduplicacion (watermarks, sync state, ids procesados)
- Patrones aprendidos del dominio (anti-patterns frecuentes, convenciones del proyecto)
- Mappings entre entidades (equipo→repos, modulo→repos)

## Que NO persiste (efimero)

- Resultados de la consulta actual → van al output al caller
- Archivos temporales de trabajo → `/tmp/` o `~/.kb-cache/` (con ciclo de vida corto)
- Contexto de conversacion → Claude lo maneja internamente

## Migracion desde MEMORY.md

Si algun agente tiene datos en `.claude/agent-memory/{agente}/MEMORY.md`, migrar al iniciar:
1. Leer el archivo con `Read`
2. Transformar al JSON apropiado
3. `kb context set {clave} '{json}' --section {agente}`
4. El archivo local puede ignorarse — KB es fuente de verdad
