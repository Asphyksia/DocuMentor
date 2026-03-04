#!/usr/bin/env python3
"""
Sync processed document data to the Streamlit dashboard.
Reads from memory/documents/ and writes dashboard-ready data to dashboard/data/.
"""

import json
import os
from pathlib import Path


def get_workspace_root():
    """Find the workspace root (parent of memory/)."""
    current = Path(__file__).resolve()
    # Navigate up from skills/dashboard/scripts/ to workspace root
    for parent in current.parents:
        if (parent / "memory").exists():
            return parent
    return Path.cwd()


def main():
    root = get_workspace_root()
    docs_dir = root / "memory" / "documents"
    dashboard_data_dir = root.parent / "dashboard" / "data"
    dashboard_data_dir.mkdir(parents=True, exist_ok=True)

    if not docs_dir.exists():
        print("No processed documents found.")
        return

    documents = []
    all_tables = []

    for json_file in sorted(docs_dir.glob("*.json")):
        with open(json_file, 'r', encoding='utf-8') as f:
            doc = json.load(f)

        documents.append({
            "filename": doc.get("filename", json_file.stem),
            "format": doc.get("format", "unknown"),
            "extracted_at": doc.get("extracted_at", ""),
            "summary": doc.get("summary", {}),
        })

        for table in doc.get("tables", []):
            all_tables.append({
                "source": doc.get("filename", json_file.stem),
                "headers": table.get("headers", []),
                "rows": table.get("rows", []),
                "row_count": len(table.get("rows", [])),
            })

    # Write documents index
    with open(dashboard_data_dir / "documents.json", 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    # Write tables data
    with open(dashboard_data_dir / "tables.json", 'w', encoding='utf-8') as f:
        json.dump(all_tables, f, ensure_ascii=False, indent=2)

    print(f"Dashboard data updated: {len(documents)} documents, {len(all_tables)} tables")


if __name__ == "__main__":
    main()
