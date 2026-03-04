---
name: rag-search
description: Semantic search over processed documents using QMD (GPU) or dotMD (CPU). Use when a user asks a question about their documents, wants to find information, compare data, or needs context from uploaded files. Also handles initial RAG backend setup and hardware detection.
---

# RAG Search

Semantic search over documents processed by `doc-ingest`.

## Backend Selection

On first run (or when `memory/config.json` doesn't have `rag_backend`), detect hardware and choose:

```bash
# Check for NVIDIA GPU
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null
```

| Hardware | Backend | Install |
|----------|---------|---------|
| NVIDIA GPU ≥ 6GB VRAM | **QMD** | `npm install -g @tobilu/qmd` |
| No GPU or < 6GB VRAM | **dotMD** | `pip install dotmd` |

Save the choice in `memory/config.json`:
```json
{
  "rag_backend": "qmd",
  "hardware_info": {
    "gpu_detected": true,
    "gpu_name": "NVIDIA RTX 3060",
    "vram_gb": 12,
    "backend_reason": "auto"
  }
}
```

## Indexing Documents

After `doc-ingest` processes a file, index it:

### QMD
```bash
qmd index --input memory/documents/<filename>.json --collection documents
```

### dotMD
```bash
python3 -m dotmd index --input memory/documents/<filename>.json --collection documents
```

## Searching

When the user asks a question:

1. Take the user's question as the query
2. Search the index for relevant chunks
3. Return the top results with source citations

### QMD
```bash
qmd search --query "<user question>" --collection documents --top-k 5
```

### dotMD
```bash
python3 -m dotmd search --query "<user question>" --collection documents --top-k 5
```

## Response Format

Always include source citations in responses:

```
[Respuesta basada en los documentos]

📄 Fuentes:
- report.pdf, página 3
- datos_2024.xlsx, hoja "Ventas"
```

## When No Results Found

If the search returns no relevant results:
```
"No he encontrado información sobre eso en los documentos disponibles.
¿Quieres que busque de otra forma o con otras palabras?"
```

Never invent or hallucinate results.

## Re-indexing

If the user uploads new documents or updates existing ones, re-index the collection:
```bash
# QMD
qmd index --input memory/documents/ --collection documents --rebuild

# dotMD
python3 -m dotmd index --input memory/documents/ --collection documents --rebuild
```
