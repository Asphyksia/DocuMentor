# TOOLS.md - Herramientas del Sistema

## RAG Backend

Búsqueda semántica con **ChromaDB** (almacenamiento vectorial local).

- Funciona en CPU sin problemas (usa embeddings all-MiniLM-L6-v2 via onnxruntime)
- GPU NVIDIA opcional (acelera embeddings si está disponible)
- Almacenamiento persistente en `memory/chromadb/`
- Config guardada en `memory/config.json` bajo `rag_backend`

### Scripts
- `skills/rag-search/scripts/setup_rag.py` — Inicializar ChromaDB
- `skills/rag-search/scripts/index.py` — Indexar documentos
- `skills/rag-search/scripts/search.py` — Buscar en documentos
- `skills/rag-search/scripts/manage.py` — Gestionar índice (list/remove/reindex/stats)

## Dashboard

- **URL**: http://localhost:8501 (Streamlit)
- Se lanza con: `cd ~/DocuMentor && streamlit run dashboard/app.py`
