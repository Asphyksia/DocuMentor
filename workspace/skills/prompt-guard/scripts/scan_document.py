#!/usr/bin/env python3
"""
Scan an extracted document for prompt injection in its content.
Runs after doc-ingest extraction, before ChromaDB indexing.

Usage:
    python3 scan_document.py <extracted_json>
"""

import json
import sys
import subprocess
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scan_document.py <extracted_json>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    filename = doc.get("filename", input_path.stem)
    scan_script = Path(__file__).parent / "scan.py"

    print(f"Scanning document: {filename}")

    threats_found = []
    chunks_scanned = 0
    chunks_flagged = 0

    # Scan all text chunks
    for i, chunk in enumerate(doc.get("chunks", [])):
        text = chunk.get("text", "").strip()
        if not text or len(text) < 20:
            continue

        chunks_scanned += 1

        # Run scan
        result = subprocess.run(
            [sys.executable, str(scan_script), "--text", text],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            continue

        try:
            scan_result = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue

        if scan_result.get("action") in ("block", "warn"):
            chunks_flagged += 1
            threat = {
                "chunk_index": i,
                "severity": scan_result.get("severity", "UNKNOWN"),
                "reasons": scan_result.get("reasons", []),
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
            }
            if "page" in chunk:
                threat["page"] = chunk["page"]
            if "sheet" in chunk:
                threat["sheet"] = chunk["sheet"]
            threats_found.append(threat)

    # Also scan table content
    for i, table in enumerate(doc.get("tables", [])):
        rows = table.get("rows", [])
        for j, row in enumerate(rows[:20]):  # Sample first 20 rows
            if isinstance(row, dict):
                text = " ".join(str(v) for v in row.values())
            else:
                text = " ".join(str(v) for v in row)

            if len(text) < 20:
                continue

            chunks_scanned += 1

            result = subprocess.run(
                [sys.executable, str(scan_script), "--text", text],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                continue

            try:
                scan_result = json.loads(result.stdout)
            except json.JSONDecodeError:
                continue

            if scan_result.get("action") in ("block", "warn"):
                chunks_flagged += 1
                threats_found.append({
                    "table_index": i,
                    "row": j,
                    "severity": scan_result.get("severity", "UNKNOWN"),
                    "reasons": scan_result.get("reasons", []),
                    "text_preview": text[:100] + "...",
                })

    # Output report
    report = {
        "filename": filename,
        "chunks_scanned": chunks_scanned,
        "chunks_flagged": chunks_flagged,
        "safe": chunks_flagged == 0,
        "threats": threats_found,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if chunks_flagged > 0:
        print(f"\n⚠️  {chunks_flagged} chunk(s) flagged in {filename}")
        print("Flagged content will be excluded from the search index.")
        sys.exit(1)  # Non-zero exit = threats found
    else:
        print(f"\n✅ Document clean: {chunks_scanned} chunks scanned, no threats.")


if __name__ == "__main__":
    main()
