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

# 2. Clean up any temporary git worktrees left by verify
echo "Pruning temporary worktrees..."
git worktree prune
rm -rf .ravel-worktrees
