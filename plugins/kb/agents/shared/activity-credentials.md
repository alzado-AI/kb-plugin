# Activity credentials — cuando y como declararlas

Una `Activity` (kind=script) que invoca `kb *` (incluyendo los subcomandos de providers — `kb google`, `kb odoo`, `kb linear`, `kb hubspot`, `kb intercom`, `kb github`, `kb metabase`, `kb figma`, `kb diio`, `kb microsoft`, `kb whatsapp`, `kb browser`) DEBE declarar credenciales al crearse:

```bash
kb activity create my-activity --kind script \
    --code-ref '{"command": "kb google gmail search is:unread --max-results 50"}' \
    --credentials '[{"type":"kb-jwt","as":"owner"}]' \
    --deterministic true
```

## Por que

Sin `--credentials`, el step corre **sin token**. El CLI del provider falla con un error opaco ("unauthenticated", "403", "no session") y el StepExecution queda con `error_code=USER_ERROR` y mensaje poco util.

## Runtime detection

El executor detecta el patron (script que invoca provider CLIs sin credenciales declaradas) y escribe un `ActivityLog` event `pipeline.script_missing_credentials` con:

```
pipeline={slug} step={name} activity={slug} provider_clis={list}
hint=Recreate Activity with --credentials '[{"type":"kb-jwt","as":"owner"}]'
```

Es un breadcrumb diagnostico, no un hard-fail — el step igual corre y falla por auth. Pero te da la pista exacta. Revisar `kb pipeline run {slug}` y el ActivityLog tras el primer run fallido.

## Inmutable post-creacion

El campo `credentials_required` de una Activity **no se puede editar** despues de crearla. Si te olvidaste de declararlas:

1. **Bump version**: crear `Activity(slug=..., version=N+1)` con las credenciales correctas; actualizar el step del pipeline para apuntar a la nueva version.
2. O **slug nuevo**: crear `Activity(slug=..., version=1)` con otro slug; deprecar la vieja.

No hay migracion in-place.

## Shapes comunes

| Caso | `credentials_required` |
|---|---|
| Script invoca `kb *` | `[{"type":"kb-jwt","as":"owner"}]` |
| Script invoca un provider del usuario (owner del pipeline) | `[{"type":"kb-jwt","as":"owner"}]` |
| Script invoca un provider del viewer (quien dispara el run) | `[{"type":"kb-jwt","as":"viewer"}]` |
| Script puro sin acceso a KB/providers (calculo local, noop) | `[]` (default, se puede omitir) |

`as=owner` usa el token del dueño del pipeline — lo que permite que runs disparados por otros usuarios hereden sus credenciales. `as=viewer` usa el token de quien dispara el run — util cuando cada usuario debe tocar sus propios datos.
