#!/usr/bin/env python3
"""Post security findings from Bandit into the #security-intake Switch room.

Spec: PLAN.md §7 Phase 6.2 and docs/HANDOFF.md Task T5.
Format:
    @sec-triager New finding <RULE> in demo-app/<file>:<line> (<function>): <message>
"""
import ast
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ravel_adapter import config

log = logging.getLogger("sec-scanner")


def find_enclosing_function(file_path, line_number):
    """Find the function enclosing line_number using AST inspection."""
    full_path = ROOT / file_path if not Path(file_path).is_absolute() else Path(file_path)
    if not full_path.exists():
        return "unknown"
    try:
        tree = ast.parse(full_path.read_text())
    except (SyntaxError, UnicodeDecodeError):
        return "unknown"

    target_fn = "module"
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", start)
            if start <= line_number <= end:
                target_fn = node.name
    return target_fn


def load_findings(findings_path=None):
    """Read findings.json or run scanner if findings.json does not exist."""
    path = Path(findings_path) if findings_path else ROOT / "findings.json"
    if not path.exists():
        scan_script = ROOT / "scripts" / "scan.sh"
        try:
            if os.name != "nt":
                subprocess.run([str(scan_script)], check=False, cwd=ROOT, capture_output=True)
            else:
                subprocess.run(["bash", str(scan_script)], check=False, cwd=ROOT, capture_output=True)
        except Exception:
            pass

    if not path.exists():
        # Fallback: run bandit directly via python
        cmd = [sys.executable, "-m", "bandit", "-r", "demo-app", "-x", "demo-app/tests",
               "-f", "json", "-o", str(path), "-q"]
        subprocess.run(cmd, check=False, cwd=ROOT, capture_output=True)

    if not path.exists():
        raise FileNotFoundError(f"Could not find or generate findings file at {path}")

    data = json.loads(path.read_text())
    results = data.get("results", [])
    # Filter out findings in tests directory (noise)
    return [r for r in results if "tests/" not in r.get("filename", "") and "/tests/" not in r.get("filename", "")]


def format_finding_message(finding):
    """Format one finding into the exact string expected by sec-triager."""
    rule = finding.get("test_id", "UNKNOWN")
    filename = finding.get("filename", "")
    line = finding.get("line_number", 0)
    msg = finding.get("issue_text", "").rstrip(".")

    # Normalize path to start with demo-app/
    rel_path = filename.replace("\\", "/")
    if rel_path.startswith("./"):
        rel_path = rel_path[2:]
    if not rel_path.startswith("demo-app/"):
        rel_path = f"demo-app/{rel_path}"

    function_name = find_enclosing_function(rel_path, line)
    return f"@sec-triager New finding {rule} in {rel_path}:{line} ({function_name}): {msg}."
