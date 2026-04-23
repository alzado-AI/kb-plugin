# Contexto organizacional — inyeccion en system prompt

Los agentes que hacen analisis, razonamiento o reporting sobre datos de la empresa deben cargar el **contexto organizacional** antes de responder. Este contexto incluye:

- Perfil de la empresa (nombre, modelo de negocio, lineas de negocio, situaciones especiales)
- Sociedades del grupo (legal entities)
- Glosario de jerga (terminos, aliases, definiciones)
- Reglas de interpretacion activas (business rules)

## Como cargar el contexto

Al arrancar, correr:

```bash
kb org-context [--module {modulo}] --format prompt
```

El output es un bloque de markdown listo para tratarlo como **contexto vinculante**. Si el agente opera en un modulo especifico (ej: `receivables`, `accounting`), pasar `--module {slug}` para filtrar el glosario y reglas relevantes.

Si `kb org-context` devuelve vacio o falla, continuar sin contexto — no es bloqueante. Pero si hay reglas o terminos activos, deben respetarse.

## Como usar el contexto

1. **Terminos del glosario son vinculantes.** Si el usuario escribe "MDO" y el glosario lo define como alias de "Petroleo Diesel Recuperado", usar la definicion canonica. No confundir terminos del glosario con su significado comun.
2. **Reglas se aplican automaticamente.** Antes de producir un reporte, analisis o recomendacion, evaluar que reglas aplican al contexto (`{tipo, subtipo, modulo, legal_entity, ...}`) y respetarlas.
3. **Cita inline.** Cuando apliques una regla, incluye el tag `[rule:{slug}]` en tu respuesta. Cuando uses una definicion no trivial, incluye `[term:{slug}]`. El frontend renderizara estos tags como links al detalle.

Ejemplo:

> En el reporte de RyD de marzo, el peso que corresponde mostrar es el de ingreso cuando ya paso por romana y por ingreso, porque es el peso oficial cobrable `[rule:romana-vs-ingreso]`.

## Que NO hacer

- No inventar terminos ni reglas que no esten en el contexto cargado.
- No asumir que el contexto sigue igual entre conversaciones — recargar al inicio de cada run.
- No filtrar el contexto por relevancia "aparente" — si el tope de 50 terminos no alcanza, reportarlo y pedir al usuario que afine el modulo.
