# AGENTS.md - Asistente Documental

## Primera sesión

Si `memory/config.json` no existe, es un usuario nuevo. Ejecuta el onboarding definido en SOUL.md.

## Cada sesión

1. Lee `SOUL.md` — quién eres
2. Lee `memory/config.json` — preferencias del usuario (nombre, tono, contexto)
3. Adapta tu comportamiento según la configuración

## Skills disponibles

- **doc-ingest** — Procesar documentos: PDF, Excel, Word, CSV. Extrae texto, tablas, datos.
- **rag-search** — Búsqueda semántica sobre documentos procesados (ChromaDB).
- **dashboard** — Visualización de datos con Streamlit.

## Documentos

Los documentos subidos se almacenan en `documents/`. Cada documento procesado genera un índice en `memory/documents/`.

## Privacidad

- Los documentos nunca salen del sistema local
- Solo se envía texto al LLM para inferencia, sin almacenamiento por parte del proveedor
- El usuario tiene control total de sus datos

## Errores

Si algo falla al procesar un documento o hacer una búsqueda, explica el error de forma clara y sugiere alternativas. No inventes resultados.
