#!/usr/bin/env python3
"""
Index extracted documents into ChromaDB for semantic search.

Usage:
    python3 index.py <extracted_json> [--db-path <path>]
    python3 index.py memory/documents/report.json
"""

import argparse
import json
import sys
import hashlib
from pathlib import Path


def find_workspace():
    """Find workspace root by looking for SOUL.md."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "SOUL.md").exists():
            return parent
    return Path.home() / ".openclaw" / "workspace"


def chunk_text(text, max_chars=2000, overlap_chars=200):
    """Split text into overlapping chunks."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end near the boundary
            for sep in [". ", ".\n", "\n\n", "\n", ". ", ", "]:
                last_sep = text.rfind(sep, start + max_chars // 2, end)
                if last_sep != -1:
                    end = last_sep + len(sep)
                    break

        chunks.append(text[start:end].strip())
        start = end - overlap_chars

    return [c for c in chunks if c]


def main():
    parser = argparse.ArgumentParser(description="Index documents into ChromaDB")
    parser.add_argument("input", help="Path to extracted JSON from doc-ingest")
    parser.add_argument("--db-path", help="Custom ChromaDB path")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    # Load extracted document
    with open(input_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    filename = doc.get("filename", input_path.stem)
    doc_format = doc.get("format", "unknown")

    print(f"Indexing: {filename} ({doc_format})")

    # Find workspace and DB path
    workspace = find_workspace()
    if args.db_path:
        db_path = Path(args.db_path)
    else:
        config_path = workspace / "memory" / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
            db_path = Path(config.get("rag_db_path", workspace / "memory" / "chromadb"))
        else:
            db_path = workspace / "memory" / "chromadb"

    # Initialize ChromaDB
    try:
        import chromadb
    except ImportError:
        print("Error: chromadb not installed. Run: pip3 install chromadb")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(db_path))
    collection = client.get_or_create_collection(name="documents")

    # First, remove any existing chunks for this document (re-index support)
    existing = collection.get(where={"source": filename})
    if existing and existing["ids"]:
        collection.delete(ids=existing["ids"])
        print(f"  Removed {len(existing['ids'])} existing chunks for {filename}")

    # Process chunks from extracted data
    all_ids = []
    all_texts = []
    all_metadatas = []

    for i, chunk in enumerate(doc.get("chunks", [])):
        text = chunk.get("text", "").strip()
        if not text or len(text) < 10:
            continue

        # Split large chunks
        sub_chunks = chunk_text(text)

        for j, sub_text in enumerate(sub_chunks):
            chunk_id = hashlib.md5(f"{filename}:{i}:{j}:{sub_text[:100]}".encode()).hexdigest()

            metadata = {
                "source": filename,
                "format": doc_format,
                "chunk_index": i,
                "sub_chunk": j,
                "type": chunk.get("type", "text"),
            }

            # Add page/sheet info if available
            if "page" in chunk:
                metadata["page"] = chunk["page"]
            if "sheet" in chunk:
                metadata["sheet"] = chunk["sheet"]

            all_ids.append(chunk_id)
            all_texts.append(sub_text)
            all_metadatas.append(metadata)

    # Also index table data as text
    for i, table in enumerate(doc.get("tables", [])):
        headers = table.get("headers", [])
        rows = table.get("rows", [])

        if not rows:
            continue

        # Convert table to readable text
        table_lines = []
        if headers:
            table_lines.append("Columnas: " + " | ".join(str(h) for h in headers))

        for row in rows[:50]:  # Limit to 50 rows per table chunk
            if isinstance(row, dict):
                line = " | ".join(str(v) for v in row.values())
            else:
                line = " | ".join(str(v) for v in row)
            table_lines.append(line)

        table_text = "\n".join(table_lines)

        # Chunk the table text too
        sub_chunks = chunk_text(table_text)

        for j, sub_text in enumerate(sub_chunks):
            chunk_id = hashlib.md5(f"{filename}:table:{i}:{j}".encode()).hexdigest()

            metadata = {
                "source": filename,
                "format": doc_format,
                "type": "table",
                "table_index": i,
                "sub_chunk": j,
                "row_count": len(rows),
            }

            if "page" in table:
                metadata["page"] = table["page"]
            if "sheet" in table:
                metadata["sheet"] = table["sheet"]

            all_ids.append(chunk_id)
            all_texts.append(sub_text)
            all_metadatas.append(metadata)

    if not all_texts:
        print(f"  Warning: No indexable content found in {filename}")
        sys.exit(0)

    # Add to ChromaDB in batches (max 5461 per batch — ChromaDB limit)
    BATCH_SIZE = 5000
    total_added = 0
    for start in range(0, len(all_texts), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(all_texts))
        collection.add(
            ids=all_ids[start:end],
            documents=all_texts[start:end],
            metadatas=all_metadatas[start:end],
        )
        total_added += end - start

    print(f"  Indexed: {total_added} chunks from {filename}")
    print(f"  Total in collection: {collection.count()} chunks")
    print(f"  Storage: {db_path}")


if __name__ == "__main__":
    main()
