#!/usr/bin/env python3
"""Reset the repository to the baseline 3-finding state for repeatable demo runs.

Cross-platform Python replacement for reset_demo.sh.
Spec: PLAN.md §7 Phase 6.3, docs/HANDOFF.md Task T4.

It only ever throws away the demo's own changes (inside demo-app/). If main has
anything else after the demo-base tag, it stops and tells you to re-tag instead.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG_NAME = "demo-base"


def git(*args, cwd=None, check=True):
    """Run a git command and return its stdout (stripped)."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, ["git", *args],
            output=result.stdout, stderr=result.stderr,
        )
    return result.stdout.strip()


def error(msg):
    """Print an error message to stderr and exit with code 1."""
    print(msg, file=sys.stderr)
    sys.exit(1)


def check_tag_exists():
    """Verify the demo-base tag exists."""
    try:
        git("rev-parse", TAG_NAME)
    except subprocess.CalledProcessError:
        error(
            f"Error: Tag '{TAG_NAME}' does not exist.\n"
            f"Create it on the baseline 3-finding commit with: git tag {TAG_NAME}"
        )


def check_uncommitted_changes():
    """Refuse if there are uncommitted changes outside demo-app/."""
    # Get status of tracked files, excluding demo-app/
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT, capture_output=True, text=True,
    )
    dirty_lines = []
    for line in result.stdout.splitlines():
        # Each line is like " M scripts/scan.sh" — the path starts at col 3
        path_part = line[3:].strip() if len(line) > 3 else ""
        path_part = path_part.replace("\\", "/")
        if path_part and not path_part.startswith("demo-app/"):
            dirty_lines.append(line)

    if dirty_lines:
        detail = "\n".join(f"  {l}" for l in dirty_lines)
        error(
            f"Error: uncommitted changes outside demo-app/ would be lost:\n"
            f"{detail}\n"
            f"Commit or stash them first."
        )


def check_tag_is_ancestor():
    """Refuse if main doesn't contain the tag (resetting would drop commits)."""
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", TAG_NAME, "main"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        error(
            f"Error: main does not contain {TAG_NAME}, so resetting would drop commits.\n"
            f"If main is the new baseline (3 findings), re-tag it: git tag -f {TAG_NAME} main"
        )


def check_no_real_work_after_tag():
    """Refuse if main has changes outside demo-app/ since the tag."""
    result = subprocess.run(
        ["git", "diff", "--name-only", TAG_NAME, "main"],
        cwd=ROOT, capture_output=True, text=True,
    )
    outside_files = []
    for line in result.stdout.splitlines():
        path = line.strip().replace("\\", "/")
        if path and not path.startswith("demo-app/"):
            outside_files.append(path)

    if outside_files:
        detail = "\n".join(f"  {f}" for f in outside_files)
        error(
            f"Error: main has changes after {TAG_NAME} outside demo-app/ "
            f"(real work, not the demo fix):\n{detail}\n"
            f"If main is the new baseline (3 findings), re-tag it: git tag -f {TAG_NAME} main"
        )


def reset_demo():
    """Main reset logic."""
    print("==> Resetting demo environment to baseline state...")

    # 1. Safety checks
    check_tag_exists()
    check_uncommitted_changes()
    check_tag_is_ancestor()
    check_no_real_work_after_tag()

    # 2. Checkout main
    current = git("rev-parse", "--abbrev-ref", "HEAD")
    if current != "main":
        print(f"Switching to main branch (was on {current})...")
        git("checkout", "--force", "main")

    # 3. Reset main to demo-base
    print(f"Resetting main to {TAG_NAME}...")
    git("reset", "--hard", TAG_NAME)

    # 4. Prune worktrees
    print("Pruning temporary worktrees...")
    git("worktree", "prune")
    worktree_dir = ROOT / ".ravel-worktrees"
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir, ignore_errors=True)

    # 5. Delete fix/* branches
    print("Cleaning up local fix/* branches...")
    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/fix/"],
        cwd=ROOT, capture_output=True, text=True,
    )
    branches = [b.strip() for b in result.stdout.splitlines() if b.strip()]
    if branches:
        for branch in branches:
            print(f"Deleting branch {branch}...")
            git("branch", "-D", branch)
    else:
        print("No local fix/* branches found.")

    # 6. Remove demo database
    print("Removing demo database...")
    demo_db = ROOT / "demo-app" / "demo.db"
    if demo_db.exists():
        demo_db.unlink()

    # 7. Verify 3 findings
    print("Verifying scanner baseline findings...")
    scan_py = ROOT / "scripts" / "scan.py"
    findings_path = ROOT / "findings.json"
    subprocess.run(
        [sys.executable, str(scan_py), "-q", "-o", str(findings_path)],
        cwd=ROOT, capture_output=True, text=True,
    )

    try:
        data = json.loads(findings_path.read_text(encoding="utf-8"))
        count = len(data.get("results", []))
    except (FileNotFoundError, json.JSONDecodeError):
        count = -1

    if count != 3:
        error(f"Error: Expected exactly 3 findings, but found {count}.")

    print("==> Demo reset complete! Baseline confirmed: 3 findings on main.")
    print("Before posting findings again, start Switch fresh: in Switch Console delete the agents\n"
          "sec-triager and sec-fixer and the rooms security-intake, security-ledger, fix-* (Remove the channel too),\n"
          "re-import switch/security-room.template.yaml, then run scripts/post_findings.py.")


if __name__ == "__main__":
    import argparse
    # Parse arguments first, so --help (or a typo) never triggers a real reset
    argparse.ArgumentParser(
        description="Reset main to the demo-base tag (3 findings) and delete local fix/* branches. "
                    "Refuses if that would drop any work outside demo-app/.",
    ).parse_args()
    reset_demo()
