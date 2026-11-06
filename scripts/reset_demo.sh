#!/usr/bin/env bash
# Resets the repository to the baseline 3-finding state for repeatable demo runs.
# Spec: PLAN.md §7 Phase 6.3, docs/HANDOFF.md Task T4.
#
# Delegates to the cross-platform Python script reset_demo.py.
# Falls back to inline logic only if Python is unavailable.
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v python3 >/dev/null 2>&1; then
    exec python3 scripts/reset_demo.py "$@"
elif command -v python >/dev/null 2>&1; then
    exec python scripts/reset_demo.py "$@"
fi

# Fallback: the original bash logic (requires bash, git, bandit)
TAG_NAME="demo-base"
echo "==> Resetting demo environment to baseline state..."

if ! git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "Error: Tag '$TAG_NAME' does not exist." >&2
    echo "Create it on the baseline 3-finding commit with: git tag demo-base" >&2
    exit 1
fi

DIRTY=$(git status --porcelain --untracked-files=no -- . ':(exclude)demo-app/')
if [ -n "$DIRTY" ]; then
    echo "Error: uncommitted changes outside demo-app/ would be lost:" >&2
    echo "$DIRTY" | sed 's/^/  /' >&2
    echo "Commit or stash them first." >&2
    exit 1
fi

if ! git merge-base --is-ancestor "$TAG_NAME" main; then
    echo "Error: main does not contain $TAG_NAME, so resetting would drop commits." >&2
    echo "If main is the new baseline (3 findings), re-tag it: git tag -f $TAG_NAME main" >&2
    exit 1
fi

OUTSIDE=$(git diff --name-only "$TAG_NAME" main -- . ':(exclude)demo-app/')
if [ -n "$OUTSIDE" ]; then
    echo "Error: main has changes after $TAG_NAME outside demo-app/ (real work, not the demo fix):" >&2
    echo "$OUTSIDE" | sed 's/^/  /' >&2
    echo "If main is the new baseline (3 findings), re-tag it: git tag -f $TAG_NAME main" >&2
    exit 1
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Switching to main branch (was on $CURRENT_BRANCH)..."
    git checkout --force main
fi

echo "Resetting main to $TAG_NAME..."
git reset --hard "$TAG_NAME"

echo "Pruning temporary worktrees..."
git worktree prune
rm -rf .ravel-worktrees

echo "Cleaning up local fix/* branches..."
FIX_BRANCHES=$(git for-each-ref --format='%(refname:short)' refs/heads/fix/ || true)
if [ -n "$FIX_BRANCHES" ]; then
    for branch in $FIX_BRANCHES; do
        echo "Deleting branch $branch..."
        git branch -D "$branch"
    done
else
    echo "No local fix/* branches found."
fi

echo "Removing demo database..."
rm -f demo-app/demo.db

echo "Verifying scanner baseline findings..."
./scripts/scan.sh >/dev/null

COUNT=$(python3 -c 'import json; print(len(json.load(open("findings.json"))["results"]))' 2>/dev/null || python -c 'import json; print(len(json.load(open("findings.json"))["results"]))')

if [ "$COUNT" -ne 3 ]; then
    echo "Error: Expected exactly 3 findings, but found $COUNT." >&2
    exit 1
fi

echo "==> Demo reset complete! Baseline confirmed: 3 findings on main."
