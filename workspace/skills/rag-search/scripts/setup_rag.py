#!/usr/bin/env python3
"""
Initialize ChromaDB for DocuMentor.
Creates persistent storage and verifies the embedding model works.

Usage:
    python3 setup_rag.py [--db-path <path>]
"""

import argparse
import sys
import json
from pathlib import Path


def find_workspace():
    """Find workspace root by looking for SOUL.md."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "SOUL.md").exists():
            return parent
    return Path.home() / ".openclaw" / "workspace"


def main():
    parser = argparse.ArgumentParser(description="Initialize ChromaDB for DocuMentor")
    parser.add_argument("--db-path", help="Custom path for ChromaDB storage")
    args = parser.parse_args()

    workspace = find_workspace()
    db_path = Path(args.db_path) if args.db_path else workspace / "memory" / "chromadb"

    print(f"Workspace: {workspace}")
    print(f"ChromaDB path: {db_path}")

    # Check ChromaDB is installed
    try:
        import chromadb
        print(f"ChromaDB version: {chromadb.__version__}")
    except ImportError:
        print("ERROR: chromadb not installed.")
        print("Run: pip3 install chromadb")
        sys.exit(1)

    # Create persistent client
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))

    # Create or get the documents collection
    collection = client.get_or_create_collection(
        name="documents",
        metadata={"description": "DocuMentor document index"}
    )

    # Test with a dummy embed to verify the model works
    print("Testing embedding model...")
    try:
        test_results = collection.query(
            query_texts=["test"],
            n_results=1
        )
        print("Embedding model: OK (default all-MiniLM-L6-v2)")
    except Exception as e:
        print(f"Warning: embedding test failed: {e}")
        print("ChromaDB will download the model on first real use.")

    # Check hardware
    gpu_info = {"gpu_detected": False, "gpu_name": None, "vram_gb": None}
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            gpu_info["gpu_detected"] = True
            gpu_info["gpu_name"] = parts[0].strip()
            if len(parts) > 1:
                mem = parts[1].strip().replace(" MiB", "")
                gpu_info["vram_gb"] = round(int(mem) / 1024, 1)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Save config
    config_path = workspace / "memory" / "config.json"
    config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    config["rag_backend"] = "chromadb"
    config["rag_db_path"] = str(db_path)
    config["hardware_info"] = gpu_info

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    count = collection.count()
    print(f"\nSetup complete:")
    print(f"  Backend: ChromaDB (persistent)")
    print(f"  Storage: {db_path}")
    print(f"  Collection: documents ({count} chunks indexed)")
    print(f"  GPU: {'Yes — ' + gpu_info['gpu_name'] if gpu_info['gpu_detected'] else 'No (using CPU — works fine)'}")
    print(f"  Config saved: {config_path}")


if __name__ == "__main__":
    main()
