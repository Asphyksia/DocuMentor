---
name: doc-ingest
description: Process uploaded documents (PDF, Excel, Word, CSV). Use when a user uploads a file or asks to process a document. Run process_document.py for the full pipeline (extract + scan + index + dashboard) in one command.
---

# Document Ingestion

## Quick Start — One Command

When a user uploads a file, run the full pipeline:

```bash
python3 {baseDir}/scripts/process_document.py <input_file>
```

This does everything automatically:
1. Extracts content (text, tables, data)
2. Scans for security threats (prompt injection)
3. Indexes in ChromaDB (semantic search)
4. Updates dashboard data

The script outputs `RESULT_JSON:{...}` with a summary. Use it to report back to the user.

## Supported Formats

| Format | Extension | Extraction |
|--------|-----------|------------|
| PDF | .pdf | Text + tables via `pdfplumber` |
| Excel | .xlsx, .xls | Sheets + data via `openpyxl` |
| Word | .docx | Text + tables via `python-docx` |
| CSV | .csv | Data via Python `csv` |

## Individual Scripts

For manual control, each step can be run separately:

- `{baseDir}/scripts/extract.py <input> <output.json>` — Extract content only
- `skills/prompt-guard/scripts/scan_document.py <json>` — Security scan only
- `skills/rag-search/scripts/index.py <json>` — Index only
- `skills/dashboard/scripts/update_dashboard.py` — Update dashboard only

## Error Handling

- Unsupported format: tell user which formats are accepted
- Extraction fails: report error, suggest checking if file is corrupted
- File too large (>100MB): warn user, suggest splitting
- Security threats: warn user, exclude flagged content from index
