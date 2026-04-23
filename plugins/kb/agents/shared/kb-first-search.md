# KB primero — obligatorio antes de generar

Antes de generar cualquier archivo, correr estas busquedas en orden:

1. `kb search "{tema}"` sin filtro — scan full-KB.
2. `kb template list --tipo {tipo}` + `kb search {keyword} --type template` — ver si hay un formato reusable.
3. `kb search {keyword} --type decision,learning,content,document` — ver reportes/decisiones previas.

Si hay un template aplicable: `kb template download SLUG --output PATH`, rellenar, y subir via `kb doc upload`. Si hay material previo relevante: leerlo e integrarlo en vez de duplicar. Solo generar from-scratch si la busqueda no devuelve nada aplicable. Solo recurrir a providers externos si la KB no tiene la informacion.
