# Report script contract — canonical pattern

Los Reports ejecutan un Pipeline cuyo ultimo step debe emitir JSON con la forma:

```json
{
  "generated_document_ids": [123],       // archivos nuevos producidos en este run
  "referenced_document_ids": [45, 67]    // docs preexistentes que el reporte consolida
}
```

Al menos uno de los dos arrays debe tener ids. Si ambos vienen vacios, la variant se marca `failed` con `CONFIG_ERROR`.

## Pattern canonico: script Python que genera xlsx + sube

```python
#!/usr/bin/env python3
"""Generate a daily cobranza report and upload as Document."""
import json
import os
import subprocess

# Params llegan como SCRIPT_VAR_* env vars (set por el workflow executor).
fecha = os.environ.get("SCRIPT_VAR_FECHA", "")

# ... build the xlsx using openpyxl/pandas into /tmp/cobranza-{fecha}.xlsx
artifact_path = f"/tmp/cobranza-{fecha}.xlsx"

# Upload the file as an internal Document.
result = subprocess.run(
    ["kb", "doc", "upload", artifact_path, "--tipo", "report"],
    capture_output=True, text=True, check=True,
)
doc = json.loads(result.stdout)

# Emit the contract as the LAST line of stdout.
print(json.dumps({"generated_document_ids": [doc["id"]]}))
```

Reglas:

- **El `print` del contrato debe ser la ultima linea de stdout.** Prints de debug → `file=sys.stderr`. Si stdout tiene ruido antes del JSON, el executor falla con "output no es JSON valido".
- **UNA sola linea de JSON.** Nada de JSON pretty-printed multi-linea.
- Si el script genera multiples Documents (varios archivos), meter todos los ids en `generated_document_ids`.

## Registrar en KB (scripts reusables, multi-linea)

```bash
kb script upload /tmp/cobranza-diaria.py \
    --slug cobranza-diaria --name "Cobranza diaria" \
    --interpreter python3 \
    --variables-schema '{"fecha":{"type":"string","required":true}}' \
    --module receivables

kb activity create cobranza-diaria-run --kind script \
    --code-ref '{"script_slug":"cobranza-diaria"}' \
    --credentials '[{"type":"kb-jwt","as":"owner"}]' \
    --deterministic true
```

Ver `.claude/agents/shared/activity-credentials.md` para la regla completa sobre `--credentials`.

## Anti-patrones

- **Command inline con `kb script download X && python3 /tmp/...`**: si ya hay Script en KB, usar `code_ref.script_slug` directamente. El workaround `command` es doble indireccion y pierde el link entre Activity y Script.
- **Script multi-linea pegado en `code_ref.command`**: va a `kb script upload` primero.
- **Multiple prints de estado antes del contrato**: redirigir a stderr, o contrato se rompe.
