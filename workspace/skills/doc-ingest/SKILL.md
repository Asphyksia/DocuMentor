---
name: doc-ingest
description: Process and extract content from uploaded documents (PDF, Excel, Word, CSV). Use when a user uploads a file, asks to process a document, or references a file they want to work with. Handles text extraction, table parsing, and data indexing for downstream search.
---

# Document Ingestion

Process uploaded documents and prepare them for semantic search.

## Supported Formats

| Format | Extension | Extraction |
|--------|-----------|------------|
| PDF | .pdf | Text + tables via `pdfplumber` |
| Excel | .xlsx, .xls | Sheets + data via `openpyxl` |
| Word | .docx | Text + tables via `python-docx` |
| CSV | .csv | Data via Python `csv` |

## Processing Flow

1. User uploads a file → saved to `documents/`
2. Detect format by extension
3. Extract content using the appropriate script in `{baseDir}/scripts/`
4. Save extracted content to `memory/documents/<filename>.json` with metadata:
   ```json
   {
     "filename": "report.pdf",
     "format": "pdf",
     "pages": 15,
     "extracted_at": "2026-03-04T12:00:00Z",
     "chunks": [...],
     "tables": [...],
     "summary": "..."
   }
   ```
5. Index content in RAG backend (see `rag-search` skill)
6. Report results to user

## Scripts

- `{baseDir}/scripts/extract.py` — Main extraction script. Usage:
  ```bash
  python3 {baseDir}/scripts/extract.py <input_file> <output_json>
  ```

## Dependencies

Install with:
```bash
pip install pdfplumber openpyxl python-docx
```

## Error Handling

- If format is unsupported: tell the user which formats are supported
- If extraction fails: report the error, suggest the user check if the file is corrupted
- If file is too large (>100MB): warn the user, suggest splitting

## After Processing

Always tell the user:
- How many pages/rows were extracted
- Suggest a first question to try
- Mention the dashboard if relevant data/tables were found
