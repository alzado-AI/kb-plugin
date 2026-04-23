# Protocolo de Contenido — Doc-First

> **Migrado a doc-first (2026-04-10).** Todo contenido de discovery se escribe directamente al Google Doc. La KB almacena metadata y referencia al documento, NO contenido.

## Protocolo actual

Ver `.claude/agents/shared/doc-first-protocol.md` para el protocolo completo de lectura/escritura de documentos.

**Resumen:**
- Contenido se escribe como markdown via `kb google doc update-tab --content-markdown-file`
- La estructura del documento viene del template `program-discovery` (tipo `pdd`)
- doc-writer es el unico agente que escribe contenido
- KB almacena metadata (estado, RICE, gates, equipo) y referencia al doc (`kb doc register`)

## Tipos de contenido

| Nivel | Tipos | Destino |
|-------|-------|---------|
| **Program** | portada, negocio, tecnica, estrategia-dev, gtm, propuesta, bitacora | Google Doc (tabs) |
| **Project** | portada, propuesta, tecnica, bitacora | Google Doc (tabs hijos dentro del doc del program) |

## Post-write lint (obligatorio)

Despues de cada escritura:
```bash
kb lint check --{entity} {SLUG} [--pretty]
```

## Protocolo legacy (deprecated)

El protocolo anterior de escritura via `kb content push` a la tabla `content` esta deprecated. Las entradas existentes en la tabla se preservan para migracion futura, pero no se escriben nuevas.
