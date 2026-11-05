"""Unit tests for scripts/reset_demo.sh logic and repeatability."""
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]


class TestResetDemoScript:
    def test_script_exists_and_is_nonempty(self):
        script = ROOT / "scripts" / "reset_demo.sh"
        assert script.exists()
        content = script.read_text()
        assert "git checkout main" in content
        assert "demo-base" in content
        assert "worktree prune" in content
        assert "demo-app/demo.db" in content
        assert "./scripts/scan.sh" in content

    def test_script_declares_strict_mode(self):
        script = ROOT / "scripts" / "reset_demo.sh"
        first_lines = script.read_text().splitlines()[:5]
        assert any("set -euo pipefail" in line for line in first_lines)

    def test_tag_demo_base_exists_in_git(self):
        result = subprocess.run(["git", "tag", "-l", "demo-base"],
                                cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0
        assert "demo-base" in result.stdout.strip()
