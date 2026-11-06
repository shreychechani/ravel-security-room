#!/usr/bin/env python3
"""Cross-platform security scanner for demo-app using Bandit.

Generates findings.json and prints human-readable output.
Expected baseline: exactly 3 findings (B608 SQL injection, B307 eval, B506 yaml.load).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_bandit():
    """Find the bandit executable, prioritizing the project's virtualenv."""
    venv_bin = ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    for name in ("bandit.exe", "bandit"):
        candidate = venv_bin / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    # Fallback to sys.executable -m bandit
    return None


def run_scan(target_dir="demo-app", exclude_dir="demo-app/tests", output_json="findings.json", quiet=False):
    """Run bandit against target_dir and write output_json."""
    output_path = ROOT / output_json if not Path(output_json).is_absolute() else Path(output_json)
    if output_path.exists():
        try:
            output_path.unlink()
        except OSError:
            pass

    bandit_bin = find_bandit()
    if bandit_bin:
        cmd = [bandit_bin, "-r", target_dir, "-x", exclude_dir, "-f", "json", "-o", str(output_path), "-q"]
    else:
        cmd = [sys.executable, "-m", "bandit", "-r", target_dir, "-x", exclude_dir,
               "-f", "json", "-o", str(output_path), "-q"]

    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    except FileNotFoundError:
        print("bandit not found: run pip install -r requirements.txt", file=sys.stderr)
        return 2

    # Bandit exits 1 when it finds security issues; that is expected.
    if proc.returncode not in (0, 1):
        print(f"Error running bandit: {proc.stderr or proc.stdout}", file=sys.stderr)
        return proc.returncode

    if not output_path.exists():
        print(f"Error: bandit did not create {output_path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Error reading scan output: {e}", file=sys.stderr)
        return 1

    results = data.get("results", [])
    if not quiet:
        for r in results:
            fname = r.get("filename", "").replace("\\", "/")
            print(f"{r.get('test_id')}  {fname}:{r.get('line_number')}  {r.get('issue_text')}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Run security scan on demo-app.")
    parser.add_argument("--output", "-o", default="findings.json", help="Path to output JSON file.")
    parser.add_argument("--target", "-t", default="demo-app", help="Directory to scan.")
    parser.add_argument("--exclude", "-x", default="demo-app/tests", help="Directory to exclude.")
    parser.add_argument("--quiet", "-q", action="store_true", help="Do not print findings to stdout.")
    args = parser.parse_args()

    code = run_scan(
        target_dir=args.target,
        exclude_dir=args.exclude,
        output_json=args.output,
        quiet=args.quiet,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()

