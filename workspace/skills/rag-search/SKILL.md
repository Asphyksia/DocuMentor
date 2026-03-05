---
name: rag-search
description: Semantic search over processed documents using ChromaDB. Use when a user asks a question about their documents, wants to find information, compare data, or needs context from uploaded files. Also handles initial RAG backend setup, document indexing, and search queries.
---

# RAG Search (ChromaDB)

Semantic search over documents processed by `doc-ingest`, powered by ChromaDB.

## Setup

On first use, initialize ChromaDB:

```bash
python3 {baseDir}/scripts/setup_rag.py
```

This creates the ChromaDB persistent storage in `{workspace}/memory/chromadb/` and detects hardware to choose the best embedding model. No GPU required — works on CPU.

## Indexing Documents

After `doc-ingest` processes a file, index it for search:

```bash
python3 {baseDir}/scripts/index.py <extracted_json>
```

Example:
```bash
python3 {baseDir}/scripts/index.py memory/documents/report.json
```

The script:
1. Reads the extracted JSON from doc-ingest
2. Splits text into searchable chunks (max ~500 tokens each)
3. Adds them to ChromaDB with source metadata (filename, page, type)
4. Reports how many chunks were indexed

## Searching

When the user asks a question about their documents:

```bash
python3 {baseDir}/scripts/search.py "<user question>" [--top-k 5]
```

Returns JSON with the most relevant chunks, scores, and source references.

Example output:
```json
{
  "query": "¿Cuántos estudiantes se matricularon en 2024?",
  "results": [
    {
      "text": "En el año 2024 se matricularon un total de 3.450 estudiantes...",
      "source": "informe_matriculas.pdf",
      "page": 7,
      "score": 0.89
    }
  ]
}
```

## Using Search Results with the LLM

When you get search results, include them as context in your response:

1. Run the search with the user's question
2. Take the top results (usually 3-5)
3. Use the text as context to answer
4. Always cite sources

Response format:
```
[Your answer based on the documents]

📄 Fuentes:
- informe_matriculas.pdf, página 7
- datos_2024.xlsx, hoja "Resumen"
```

## When No Results Found

If search returns no relevant results (all scores below 0.3):
```
"No he encontrado información sobre eso en los documentos disponibles.
¿Quieres que busque con otras palabras?"
```

Never invent or hallucinate results.

## Managing the Index

List indexed documents:
```bash
python3 {baseDir}/scripts/manage.py list
```

Remove a document from the index:
```bash
python3 {baseDir}/scripts/manage.py remove <filename>
```

Re-index everything:
```bash
python3 {baseDir}/scripts/manage.py reindex
```

## Technical Details

- **Storage**: `{workspace}/memory/chromadb/` (persistent, survives restarts)
- **Embeddings**: ChromaDB default (all-MiniLM-L6-v2 via onnxruntime, runs on CPU)
- **Chunk size**: ~500 tokens with 50-token overlap
- **Collection**: `documents` (single collection for all user docs)
