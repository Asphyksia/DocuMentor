#!/usr/bin/env python3
"""
Semantic search over indexed documents using ChromaDB.

Usage:
    python3 search.py "<query>" [--top-k 5] [--db-path <path>] [--min-score 0.3]
"""

import argparse
import json
import sys
from pathlib import Path


def find_workspace():
    """Find workspace root by looking for SOUL.md."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "SOUL.md").exists():
            return parent
    return Path.home() / ".openclaw" / "workspace"


def main():
    parser = argparse.ArgumentParser(description="Search documents with ChromaDB")
    parser.add_argument("query", help="Search query in natural language")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--min-score", type=float, default=0.3, help="Minimum relevance score 0-1 (default: 0.3)")
    parser.add_argument("--db-path", help="Custom ChromaDB path")
    parser.add_argument("--source", help="Filter by source filename")
    args = parser.parse_args()

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

    if not db_path.exists():
        print(json.dumps({
            "query": args.query,
            "error": "ChromaDB not initialized. Run setup_rag.py first.",
            "results": []
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Initialize ChromaDB
    try:
        import chromadb
    except ImportError:
        print(json.dumps({
            "query": args.query,
            "error": "chromadb not installed. Run: pip3 install chromadb",
            "results": []
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(db_path))

    try:
        collection = client.get_collection(name="documents")
    except Exception:
        print(json.dumps({
            "query": args.query,
            "error": "No documents indexed yet. Upload and process a document first.",
            "results": []
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    if collection.count() == 0:
        print(json.dumps({
            "query": args.query,
            "error": "Collection is empty. Upload and process a document first.",
            "results": []
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    # Build query parameters
    query_params = {
        "query_texts": [args.query],
        "n_results": min(args.top_k, collection.count()),
    }

    if args.source:
        query_params["where"] = {"source": args.source}

    # Search
    results = collection.query(**query_params)

    # Format results
    formatted = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc_text in enumerate(results["documents"][0]):
            # ChromaDB returns distances, convert to similarity score (0-1)
            distance = results["distances"][0][i] if results["distances"] else 0
            # ChromaDB uses L2 distance by default; convert to a 0-1 score
            # Lower distance = more similar
            score = round(max(0, 1 - (distance / 2)), 3)

            if score < args.min_score:
                continue

            metadata = results["metadatas"][0][i] if results["metadatas"] else {}

            result = {
                "text": doc_text,
                "source": metadata.get("source", "unknown"),
                "score": score,
                "type": metadata.get("type", "text"),
            }

            if "page" in metadata:
                result["page"] = metadata["page"]
            if "sheet" in metadata:
                result["sheet"] = metadata["sheet"]

            formatted.append(result)

    output = {
        "query": args.query,
        "total_indexed": collection.count(),
        "results_count": len(formatted),
        "results": formatted,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
