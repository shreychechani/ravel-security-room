#!/usr/bin/env bash
# Resets the repository to the baseline 3-finding state for repeatable demo runs.
# Spec: PLAN.md §7 Phase 6.3, docs/HANDOFF.md Task T4.
#
# It only ever throws away the demo's own changes (inside demo-app/). If main has
# anything else after the demo-base tag, it stops and tells you to re-tag instead.
set -euo pipefail

cd "$(dirname "$0")/.."

TAG_NAME="demo-base"
echo "==> Resetting demo environment to baseline state..."

# 1. Safety checks, before anything changes
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

# 2. Checkout main (only demo-app/ changes can be left over at this point)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Switching to main branch (was on $CURRENT_BRANCH)..."
    git checkout --force main
fi

# 3. Reset main to demo-base: undoes the demo's fix merge
echo "Resetting main to $TAG_NAME..."
git reset --hard "$TAG_NAME"

# 4. Clean up any temporary git worktrees left by verify
echo "Pruning temporary worktrees..."
git worktree prune
rm -rf .ravel-worktrees

# 5. Delete all local fix/* branches
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

# 6. Remove the demo database
echo "Removing demo database..."
rm -f demo-app/demo.db

# 7. Re-run scan and verify exactly 3 findings exist
echo "Verifying scanner baseline findings..."
./scripts/scan.sh >/dev/null

COUNT=$(python3 -c 'import json; print(len(json.load(open("findings.json"))["results"]))' 2>/dev/null || python -c 'import json; print(len(json.load(open("findings.json"))["results"]))')

if [ "$COUNT" -ne 3 ]; then
    echo "Error: Expected exactly 3 findings, but found $COUNT." >&2
    exit 1
fi

echo "==> Demo reset complete! Baseline confirmed: 3 findings on main."
