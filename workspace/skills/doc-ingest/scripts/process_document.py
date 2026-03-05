#!/usr/bin/env python3
"""
Full document processing pipeline. One command, does everything:
  1. Extract content (PDF/Excel/Word/CSV)
  2. Security scan (prompt injection detection)
  3. Index in ChromaDB (semantic search)
  4. Update dashboard data

Usage:
    python3 process_document.py <input_file>

The agent only needs to call THIS script. Everything else is automatic.
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone


def find_workspace():
    """Find workspace root by looking for SOUL.md."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "SOUL.md").exists():
            return parent
    return Path.home() / ".openclaw" / "workspace"


def run_script(script_path, args, step_name):
    """Run a script and return (success, output)."""
    cmd = [sys.executable, str(script_path)] + args
    print(f"\n{'='*50}")
    print(f"  PASO: {step_name}")
    print(f"  CMD:  {' '.join(cmd)}")
    print(f"{'='*50}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"  STDERR: {result.stderr}", file=sys.stderr)

    return result.returncode == 0, result.stdout, result.stderr


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 process_document.py <input_file>")
        print("Supported: PDF, Excel (.xlsx/.xls), Word (.docx), CSV")
        sys.exit(1)

    input_file = Path(sys.argv[1]).resolve()
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    # Check supported format
    supported = {'.pdf', '.xlsx', '.xls', '.docx', '.csv'}
    if input_file.suffix.lower() not in supported:
        print(f"Error: Formato no soportado: {input_file.suffix}")
        print(f"Formatos válidos: {', '.join(sorted(supported))}")
        sys.exit(1)

    workspace = find_workspace()
    skills_dir = workspace / "skills"
    docs_dir = workspace / "memory" / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Also copy the file to documents/ for reference
    user_docs_dir = workspace / "documents"
    user_docs_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    dest_file = user_docs_dir / input_file.name
    if input_file != dest_file:
        shutil.copy2(str(input_file), str(dest_file))

    output_json = docs_dir / f"{input_file.stem}.json"
    filename = input_file.name

    print(f"\n📄 Procesando: {filename}")
    print(f"   Workspace: {workspace}")

    results = {
        "filename": filename,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "steps": {}
    }

    # ── Step 1: Extract ─────────────────────────────────
    extract_script = skills_dir / "doc-ingest" / "scripts" / "extract.py"
    if not extract_script.exists():
        print(f"Error: extract.py not found at {extract_script}")
        sys.exit(1)

    success, stdout, stderr = run_script(
        extract_script,
        [str(input_file), str(output_json)],
        "1/4 · Extracción de contenido"
    )

    if not success:
        print(f"\n❌ Error en extracción: {stderr}")
        results["steps"]["extract"] = {"status": "failed", "error": stderr}
        print(json.dumps(results, ensure_ascii=False, indent=2))
        sys.exit(1)

    results["steps"]["extract"] = {"status": "ok"}

    # Read extracted data for stats
    with open(output_json, "r", encoding="utf-8") as f:
        extracted = json.load(f)

    chunks_count = len(extracted.get("chunks", []))
    tables_count = len(extracted.get("tables", []))
    total_chars = extracted.get("summary", {}).get("total_chars", 0)

    print(f"  → {chunks_count} chunks, {tables_count} tablas, {total_chars:,} caracteres")

    # ── Step 2: Security Scan ───────────────────────────
    scan_script = skills_dir / "prompt-guard" / "scripts" / "scan_document.py"
    threats_found = False

    if scan_script.exists():
        success, stdout, stderr = run_script(
            scan_script,
            [str(output_json)],
            "2/4 · Escaneo de seguridad"
        )

        if not success:
            # Non-zero exit = threats found
            threats_found = True
            results["steps"]["security_scan"] = {
                "status": "threats_found",
                "details": stdout
            }
            print("  ⚠️  Amenazas detectadas. Los chunks flaggeados se excluirán del índice.")
        else:
            results["steps"]["security_scan"] = {"status": "clean"}
            print("  ✅ Documento limpio")
    else:
        results["steps"]["security_scan"] = {"status": "skipped", "reason": "scan script not found"}
        print("  ⚠️  prompt-guard no disponible, saltando escaneo")

    # ── Step 3: Index in ChromaDB ───────────────────────
    index_script = skills_dir / "rag-search" / "scripts" / "index.py"

    if index_script.exists():
        # Initialize ChromaDB if needed
        setup_script = skills_dir / "rag-search" / "scripts" / "setup_rag.py"
        config_path = workspace / "memory" / "config.json"

        if setup_script.exists() and not config_path.exists():
            run_script(setup_script, [], "2.5/4 · Inicializando ChromaDB (primera vez)")

        success, stdout, stderr = run_script(
            index_script,
            [str(output_json)],
            "3/4 · Indexación en ChromaDB"
        )

        if success:
            results["steps"]["index"] = {"status": "ok"}
        else:
            results["steps"]["index"] = {"status": "failed", "error": stderr}
            print(f"  ⚠️  Error indexando, pero el documento fue extraído correctamente")
    else:
        results["steps"]["index"] = {"status": "skipped", "reason": "index script not found"}

    # ── Step 4: Update Dashboard ────────────────────────
    dashboard_script = skills_dir / "dashboard" / "scripts" / "update_dashboard.py"

    if dashboard_script.exists():
        success, stdout, stderr = run_script(
            dashboard_script,
            [],
            "4/4 · Actualizando dashboard"
        )

        if success:
            results["steps"]["dashboard"] = {"status": "ok"}
        else:
            results["steps"]["dashboard"] = {"status": "failed", "error": stderr}
            print(f"  ⚠️  Dashboard no actualizado, pero el documento está procesado")
    else:
        results["steps"]["dashboard"] = {"status": "skipped"}

    # ── Summary ─────────────────────────────────────────
    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["summary"] = {
        "chunks": chunks_count,
        "tables": tables_count,
        "characters": total_chars,
        "threats_found": threats_found,
        "format": extracted.get("format", "unknown"),
        "pages": extracted.get("pages", None),
        "sheets": extracted.get("sheets", None),
    }

    # Determine overall status
    all_ok = all(
        s.get("status") in ("ok", "clean", "skipped")
        for s in results["steps"].values()
    )
    results["status"] = "ok" if all_ok else "partial"

    print(f"\n{'='*50}")
    if all_ok:
        print(f"  ✅ {filename} procesado correctamente")
    else:
        print(f"  ⚠️  {filename} procesado con advertencias")
    print(f"     Chunks: {chunks_count} | Tablas: {tables_count} | Chars: {total_chars:,}")
    if threats_found:
        print(f"     ⚠️  Se detectaron contenidos sospechosos")
    print(f"{'='*50}\n")

    # Output JSON summary (the agent can parse this)
    print("RESULT_JSON:" + json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
