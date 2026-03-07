#!/usr/bin/env python3
"""
Manage the ChromaDB document index.

Usage:
    python3 manage.py list                    # List indexed documents
    python3 manage.py remove <filename>       # Remove a document from index
    python3 manage.py reindex                 # Re-index all documents
    python3 manage.py stats                   # Show index statistics
"""

import argparse
import json
import sys
import os
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import subprocess
from pathlib import Path
from collections import Counter


def find_workspace():
    """Find workspace root by looking for SOUL.md."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "SOUL.md").exists():
            return parent
    return Path.home() / ".openclaw" / "workspace"


def get_client(workspace, db_path_override=None):
    """Get ChromaDB client."""
    import chromadb

    if db_path_override:
        db_path = Path(db_path_override)
    else:
        config_path = workspace / "memory" / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
            db_path = Path(config.get("rag_db_path", workspace / "memory" / "chromadb"))
        else:
            db_path = workspace / "memory" / "chromadb"

    if not db_path.exists():
        print("Error: ChromaDB not initialized. Run setup_rag.py first.")
        sys.exit(1)

    return chromadb.PersistentClient(path=str(db_path))


def cmd_list(client):
    """List all indexed documents."""
    try:
        collection = client.get_collection("documents")
    except Exception:
        print("No documents indexed yet.")
        return

    all_data = collection.get()
    if not all_data["metadatas"]:
        print("No documents indexed yet.")
        return

    # Count chunks per source
    sources = Counter()
    for meta in all_data["metadatas"]:
        sources[meta.get("source", "unknown")] += 1

    print(f"Indexed documents ({len(sources)} files, {collection.count()} total chunks):\n")
    for source, count in sorted(sources.items()):
        print(f"  📄 {source} — {count} chunks")
    print()


def cmd_remove(client, filename):
    """Remove a document from the index."""
    try:
        collection = client.get_collection("documents")
    except Exception:
        print("No documents indexed.")
        return

    existing = collection.get(where={"source": filename})
    if not existing["ids"]:
        print(f"Document not found in index: {filename}")
        return

    collection.delete(ids=existing["ids"])
    print(f"Removed {len(existing['ids'])} chunks for: {filename}")
    print(f"Remaining: {collection.count()} chunks")


def cmd_reindex(workspace):
    """Re-index all documents from memory/documents/."""
    docs_dir = workspace / "memory" / "documents"
    if not docs_dir.exists():
        print("No processed documents found in memory/documents/")
        return

    json_files = sorted(docs_dir.glob("*.json"))
    if not json_files:
        print("No processed documents found.")
        return

    index_script = Path(__file__).parent / "index.py"
    print(f"Re-indexing {len(json_files)} documents...\n")

    for json_file in json_files:
        print(f"  → {json_file.name}")
        result = subprocess.run(
            [sys.executable, str(index_script), str(json_file)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"    Error: {result.stderr.strip()}")
        else:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    print(f"    {line.strip()}")

    print("\nRe-indexing complete.")


def cmd_stats(client):
    """Show index statistics."""
    try:
        collection = client.get_collection("documents")
    except Exception:
        print("No index found.")
        return

    all_data = collection.get()
    if not all_data["metadatas"]:
        print("Index is empty.")
        return

    sources = Counter()
    types = Counter()
    total_chars = 0

    for i, meta in enumerate(all_data["metadatas"]):
        sources[meta.get("source", "unknown")] += 1
        types[meta.get("type", "text")] += 1
        if all_data["documents"] and i < len(all_data["documents"]):
            total_chars += len(all_data["documents"][i] or "")

    print(f"Index Statistics:")
    print(f"  Total chunks: {collection.count()}")
    print(f"  Total characters: {total_chars:,}")
    print(f"  Documents: {len(sources)}")
    print(f"  Chunk types: {dict(types)}")
    print()
    print(f"  By document:")
    for source, count in sorted(sources.items()):
        print(f"    {source}: {count} chunks")


def main():
    parser = argparse.ArgumentParser(description="Manage ChromaDB document index")
    parser.add_argument("command", choices=["list", "remove", "reindex", "stats"])
    parser.add_argument("filename", nargs="?", help="Filename for remove command")
    parser.add_argument("--db-path", help="Custom ChromaDB path")
    args = parser.parse_args()

    workspace = find_workspace()

    try:
        import chromadb
    except ImportError:
        print("Error: chromadb not installed. Run: pip3 install chromadb")
        sys.exit(1)

    if args.command == "reindex":
        cmd_reindex(workspace)
    else:
        client = get_client(workspace, args.db_path)
        if args.command == "list":
            cmd_list(client)
        elif args.command == "remove":
            if not args.filename:
                print("Error: filename required for remove command")
                sys.exit(1)
            cmd_remove(client, args.filename)
        elif args.command == "stats":
            cmd_stats(client)


if __name__ == "__main__":
    main()
