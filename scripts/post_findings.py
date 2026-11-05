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


import argparse
import time
import requests


def get_room_id(base_url, agent_id, api_key, room_name="security-intake"):
    """Find the ID of the intake room using the list_rooms operation."""
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.post(f"{base_url}/agents/{agent_id}/ops/list_rooms",
                         headers=headers, json={}, timeout=15)
    resp.raise_for_status()
    rooms = resp.json().get("result") or []
    for r in rooms:
        name = r.get("name") or r.get("display_name") or ""
        if name.strip("#") == room_name.strip("#"):
            return r.get("id") or r.get("room_id")
    raise ValueError(f"Room '{room_name}' not found among rooms: {[r.get('name') for r in rooms]}")


def post_message(base_url, agent_id, api_key, room_id, content):
    """Post one message into a room via HTTP."""
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.post(f"{base_url}/agents/{agent_id}/message",
                         headers=headers, json={"room_id": room_id, "content": content},
                         timeout=15)
    resp.raise_for_status()


def post_all_findings(base_url=None, agent_id=None, api_key=None,
                      room_name="security-intake", interval=2.0,
                      dry_run=False, findings_path=None):
    """Scan and post each finding into the security intake room."""
    findings = load_findings(findings_path)
    messages = [format_finding_message(f) for f in findings]

    print(f"Loaded {len(messages)} findings to post:")
    for msg in messages:
        print(f"  • {msg}")

    if dry_run:
        print("\nDry-run mode: no messages sent to Switch.")
        return messages

    base_url = (base_url or config.SWITCH_URL).rstrip("/")
    agent_id = agent_id or config.SCANNER_AGENT_ID
    api_key = api_key or config.SCANNER_AGENT_KEY

    if not (agent_id and api_key):
        raise ValueError(
            "SCANNER_AGENT_ID and SCANNER_AGENT_KEY must be configured in .env or arguments. "
            "Register the agent first: python -m ravel_adapter.register sec-scanner"
        )

    room_id = get_room_id(base_url, agent_id, api_key, room_name)
    print(f"\nPosting to room '{room_name}' (ID: {room_id}) via {base_url}...")

    for i, msg in enumerate(messages, 1):
        post_message(base_url, agent_id, api_key, room_id, msg)
        print(f"[{i}/{len(messages)}] Posted: {msg[:65]}...")
        if i < len(messages) and interval > 0:
            time.sleep(interval)

    print("All findings posted successfully.")
    return messages


def main():
    parser = argparse.ArgumentParser(description="Post security scan findings into Switch room.")
    parser.add_argument("--dry-run", action="store_true", help="Format and print findings without sending.")
    parser.add_argument("--room", default="security-intake", help="Target room name (default: security-intake).")
    parser.add_argument("--interval", type=float, default=2.0, help="Delay between posts in seconds (default: 2.0).")
    parser.add_argument("--findings", default=None, help="Path to findings.json file.")
    args = parser.parse_args()

    post_all_findings(
        room_name=args.room,
        interval=args.interval,
        dry_run=args.dry_run,
        findings_path=args.findings,
    )


if __name__ == "__main__":
    main()
