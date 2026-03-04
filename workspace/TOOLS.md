# TOOLS.md - Herramientas del Sistema

## RAG Backend

El backend de búsqueda semántica se configura automáticamente:

- **QMD** — Si hay GPU NVIDIA con ≥6GB VRAM (búsqueda vectorial, más rápido)
- **dotMD** — Si no hay GPU (CPU, más portable)

El backend elegido se guarda en `memory/config.json` bajo `rag_backend`.

## Dashboard

- **URL**: http://localhost:8501 (Streamlit)
- Se lanza automáticamente con el sistema
