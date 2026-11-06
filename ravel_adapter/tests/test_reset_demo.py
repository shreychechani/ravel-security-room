"""Tests for scripts/reset_demo.sh: static checks, plus real runs in throwaway git repos."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "reset_demo.sh"

# Stands in for scripts/scan.sh in the throwaway repo: always "finds" 3 issues.
FAKE_SCAN = """#!/usr/bin/env bash
echo '{"results": [{}, {}, {}]}' > findings.json
"""


class TestResetDemoScript:
    def test_script_exists_and_is_nonempty(self):
        assert SCRIPT.exists()
        content = SCRIPT.read_text()
        assert "git checkout --force main" in content
        assert "demo-base" in content
        assert "worktree prune" in content
        assert "demo-app/demo.db" in content
        assert "./scripts/scan.sh" in content

    def test_script_declares_strict_mode(self):
        first_lines = SCRIPT.read_text().splitlines()[:10]
        assert any("set -euo pipefail" in line for line in first_lines)

    def test_tag_demo_base_exists_in_git(self):
        result = subprocess.run(["git", "tag", "-l", "demo-base"],
                                cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0
        assert "demo-base" in result.stdout.strip()


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()


def commit(repo, path, text, message):
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text)
    git(repo, "add", path)
    git(repo, "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path):
    """A tiny repo shaped like ours: demo-app/, scripts/, main tagged demo-base."""
    if shutil.which("git") is None or shutil.which("bash") is None:
        pytest.skip("needs git and bash")
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "test")
    (repo / "scripts").mkdir()
    shutil.copy(SCRIPT, repo / "scripts" / "reset_demo.sh")
    (repo / "scripts" / "scan.sh").write_text(FAKE_SCAN)
    (repo / "scripts" / "scan.sh").chmod(0o755)
    (repo / ".gitignore").write_text("findings.json\n")
    commit(repo, "demo-app/app.py", "query = 'unsafe'\n", "baseline")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "scripts")
    git(repo, "tag", "demo-base")
    return repo


def run_reset(repo):
    return subprocess.run(["bash", "scripts/reset_demo.sh"], cwd=repo,
                          capture_output=True, text=True)


def test_undoes_the_demo_fix_and_deletes_fix_branches(repo):
    git(repo, "checkout", "-q", "-b", "fix/sqli-search")
    commit(repo, "demo-app/app.py", "query = 'safe'\n", "fix")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "fix/sqli-search", "-m", "merge fix")

    result = run_reset(repo)

    assert result.returncode == 0, result.stderr
    assert (repo / "demo-app/app.py").read_text() == "query = 'unsafe'\n"
    assert git(repo, "rev-parse", "main") == git(repo, "rev-parse", "demo-base")
    assert git(repo, "branch", "--list", "fix/*") == ""


def test_running_twice_is_fine(repo):
    assert run_reset(repo).returncode == 0
    assert run_reset(repo).returncode == 0


def test_refuses_when_main_has_real_work_after_the_tag(repo):
    commit(repo, "scripts/new_tool.py", "print('new work')\n", "teammate work")
    head = git(repo, "rev-parse", "main")

    result = run_reset(repo)

    assert result.returncode == 1
    assert "outside demo-app/" in result.stderr and "git tag -f demo-base main" in result.stderr
    assert git(repo, "rev-parse", "main") == head          # nothing was thrown away


def test_refuses_with_uncommitted_changes_outside_demo_app(repo):
    (repo / "scripts" / "scan.sh").write_text(FAKE_SCAN + "# edited\n")

    result = run_reset(repo)

    assert result.returncode == 1
    assert "uncommitted changes" in result.stderr
    assert (repo / "scripts" / "scan.sh").read_text().endswith("# edited\n")


def test_refuses_when_main_does_not_contain_the_tag(repo):
    git(repo, "tag", "-f", "demo-base", git(repo, "rev-parse", "HEAD"))
    git(repo, "checkout", "-q", "--orphan", "other")
    commit(repo, "demo-app/app.py", "x\n", "unrelated")
    git(repo, "tag", "-f", "demo-base", "HEAD")
    git(repo, "checkout", "-q", "main")

    result = run_reset(repo)

    assert result.returncode == 1
    assert "does not contain demo-base" in result.stderr
