# Protocolo de Esperas (Parkeo)

Shared entre `/kb:program` y `/kb:project`. Parametros:
- `{ENTITY_TYPE}`: `program` o `project`
- `{SLUG}`: slug de la entidad

**Tipos comunes:** `feedback` (auto-check de doc comments al retomar), `reunion`, `decision`, `pausa`. En `/kb:project` agregan: `review` (auto-check de CI + review status via code-host provider), `diseno` (preguntar al usuario).

## Parkear

1. `kb espera create {tipo} --{ENTITY_TYPE} {SLUG} --detalle "{detalle}" [--source-ref "{ref}"]`
2. `kb {ENTITY_TYPE} update {SLUG} --bloqueado true`
3. Informar al usuario.

## Retomar

1. `kb espera list --{ENTITY_TYPE} {SLUG} --active`
2. Auto-verificar las esperas con `source_ref` (`feedback` → doc comments; `review` → PR/CI status; `decision` → comentarios del issue).
3. `kb espera resolve {ID}` si se resolvio.
4. `kb {ENTITY_TYPE} update {SLUG} --bloqueado false` si ya no hay bloqueos.
