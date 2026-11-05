#!/usr/bin/env bash
# Resets the repository to the baseline 3-finding state for repeatable demo runs.
# Spec: PLAN.md §7 Phase 6.3, docs/HANDOFF.md Task T4.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Resetting demo environment to baseline state..."

# 1. Checkout main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Switching to main branch (was on $CURRENT_BRANCH)..."
    git checkout main
fi

# 2. Reset main to demo-base tag
TAG_NAME="demo-base"
if ! git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "Error: Tag '$TAG_NAME' does not exist." >&2
    echo "Create it on the baseline 3-finding commit with: git tag demo-base" >&2
    exit 1
fi

echo "Resetting main to $TAG_NAME..."
git reset --hard "$TAG_NAME"

# 3. Clean up any temporary git worktrees left by verify
echo "Pruning temporary worktrees..."
git worktree prune
rm -rf .ravel-worktrees

# 4. Delete all local fix/* branches
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
