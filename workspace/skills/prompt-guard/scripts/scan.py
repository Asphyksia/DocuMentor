#!/usr/bin/env python3
"""
Scan text for prompt injection attacks using prompt-guard.

Usage:
    python3 scan.py --text "user message here"
    python3 scan.py --text "llm response" --mode output
    python3 scan.py --file /path/to/file.txt
"""

import argparse
import json
import sys


def get_config():
    """Load prompt guard config from workspace."""
    from pathlib import Path
    current = Path(__file__).resolve()
    for parent in current.parents:
        config_path = parent / "memory" / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
            return config.get("prompt_guard", {})
    return {}


def main():
    parser = argparse.ArgumentParser(description="Scan text for prompt injection")
    parser.add_argument("--text", help="Text to scan")
    parser.add_argument("--file", help="File to scan")
    parser.add_argument("--mode", choices=["input", "output"], default="input",
                        help="Scan mode: input (user messages) or output (LLM responses)")
    parser.add_argument("--sensitivity", choices=["low", "medium", "high", "paranoid"],
                        help="Override sensitivity level")
    parser.add_argument("--json", action="store_true", default=True,
                        help="Output as JSON (default)")
    args = parser.parse_args()

    # Get text to scan
    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        # Read from stdin
        text = sys.stdin.read()

    if not text.strip():
        print(json.dumps({"action": "allow", "severity": "SAFE", "reasons": []}))
        return

    # Try to import prompt_guard
    try:
        from prompt_guard import PromptGuard
    except ImportError:
        # Fallback: basic pattern matching if prompt-guard not installed
        result = basic_scan(text)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Load config
    config = get_config()
    sensitivity = args.sensitivity or config.get("sensitivity", "medium")

    # Initialize guard
    guard_config = {
        "sensitivity": sensitivity,
        "api": {"enabled": False}  # Fully offline
    }
    guard = PromptGuard(config=guard_config)

    # Scan
    if args.mode == "output":
        result = guard.scan_output(text)
    else:
        result = guard.analyze(text)

    # Format output
    output = {
        "action": getattr(result, "action", "allow"),
        "severity": getattr(result, "severity", "SAFE"),
        "reasons": getattr(result, "reasons", []),
        "score": getattr(result, "score", 0),
    }

    # Add matches detail if available
    if hasattr(result, "matches") and result.matches:
        output["matches"] = [
            {
                "pattern": getattr(m, "pattern", str(m)),
                "category": getattr(m, "category", "unknown"),
                "severity": getattr(m, "severity", "unknown"),
            }
            for m in result.matches[:10]  # Limit to 10 matches
        ]

    print(json.dumps(output, ensure_ascii=False, indent=2))


def basic_scan(text):
    """
    Basic fallback scanner when prompt-guard is not installed.
    Catches the most obvious injection patterns.
    """
    import re

    threats = []
    text_lower = text.lower()

    # Critical patterns
    critical_patterns = [
        (r"ignore\s+(all\s+)?previous\s+instructions", "instruction_override"),
        (r"ignore\s+(all\s+)?prior\s+instructions", "instruction_override"),
        (r"disregard\s+(all\s+)?previous", "instruction_override"),
        (r"forget\s+(all\s+)?(your|previous)\s+instructions", "instruction_override"),
        (r"you\s+are\s+now\s+(?:a|an)\s+", "role_hijack"),
        (r"act\s+as\s+(?:a|an)\s+(?:different|new)", "role_hijack"),
        (r"new\s+system\s+prompt", "system_prompt_injection"),
        (r"system:\s*you\s+are", "system_prompt_injection"),
        (r"show\s+me\s+your\s+(api|secret|token|key|password)", "secret_exfil"),
        (r"what\s+is\s+your\s+(api|secret|token|key|password)", "secret_exfil"),
        (r"reveal\s+(your|the)\s+(api|secret|token|key|password|prompt)", "secret_exfil"),
        (r"print\s+(your|the)\s+system\s+prompt", "secret_exfil"),
        (r"output\s+(your|the)\s+(full\s+)?system\s+(prompt|message)", "secret_exfil"),
        (r"bash\s+-[ci]|/dev/tcp|nc\s+-[el]|curl\s+.*\|\s*bash", "command_injection"),
        (r"rm\s+-rf\s+/|mkfs\.|dd\s+if=", "destructive_command"),
    ]

    # High patterns (Spanish)
    high_patterns_es = [
        (r"ignora\s+(todas?\s+)?(las\s+)?instrucciones\s+anteriores", "instruction_override_es"),
        (r"olvida\s+(todas?\s+)?(las\s+)?instrucciones", "instruction_override_es"),
        (r"muéstrame\s+(tu|la)\s+(clave|contraseña|token|api)", "secret_exfil_es"),
        (r"ahora\s+eres\s+(?:un|una)\s+", "role_hijack_es"),
    ]

    all_patterns = critical_patterns + high_patterns_es

    for pattern, name in all_patterns:
        if re.search(pattern, text_lower):
            threats.append(name)

    if not threats:
        return {"action": "allow", "severity": "SAFE", "reasons": [], "fallback": True}

    # Determine severity
    critical_names = {"command_injection", "destructive_command", "system_prompt_injection"}
    if any(t in critical_names for t in threats):
        severity = "CRITICAL"
        action = "block"
    elif len(threats) >= 2:
        severity = "HIGH"
        action = "block"
    else:
        severity = "MEDIUM"
        action = "warn"

    return {
        "action": action,
        "severity": severity,
        "reasons": threats,
        "fallback": True,
        "note": "Using basic scanner. Install prompt-guard for full protection: pip install prompt-guard"
    }


if __name__ == "__main__":
    main()
