"""Tests for scripts/reset_demo.py: static checks, plus real runs in throwaway git repos."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PY = ROOT / "scripts" / "reset_demo.py"
SCRIPT_SH = ROOT / "scripts" / "reset_demo.sh"

# Stands in for scripts/scan.py in the throwaway repo: always "finds" 3 issues.
FAKE_SCAN_PY = """\
import json, sys
out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else "findings.json"
with open(out, "w") as f:
    json.dump({"results": [{}, {}, {}]}, f)
"""


class TestResetDemoScript:
    def test_python_script_exists_and_is_nonempty(self):
        assert SCRIPT_PY.exists()
        content = SCRIPT_PY.read_text()
        assert "demo-base" in content
        assert "worktree" in content
        assert "demo-app" in content

    def test_bash_script_exists_and_delegates(self):
        assert SCRIPT_SH.exists()
        content = SCRIPT_SH.read_text()
        assert "reset_demo.py" in content

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
    if shutil.which("git") is None:
        pytest.skip("needs git")
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "test")
    (repo / "scripts").mkdir()
    shutil.copy(SCRIPT_PY, repo / "scripts" / "reset_demo.py")
    (repo / "scripts" / "scan.py").write_text(FAKE_SCAN_PY)
    (repo / ".gitignore").write_text("findings.json\n")
    commit(repo, "demo-app/app.py", "query = 'unsafe'\n", "baseline")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "scripts")
    git(repo, "tag", "demo-base")
    return repo


def run_reset(repo):
    return subprocess.run([sys.executable, "scripts/reset_demo.py"], cwd=repo,
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
    (repo / "scripts" / "scan.py").write_text(FAKE_SCAN_PY + "# edited\n")

    result = run_reset(repo)

    assert result.returncode == 1
    assert "uncommitted changes" in result.stderr
    assert (repo / "scripts" / "scan.py").read_text().endswith("# edited\n")


def test_refuses_when_main_does_not_contain_the_tag(repo):
    git(repo, "tag", "-f", "demo-base", git(repo, "rev-parse", "HEAD"))
    git(repo, "checkout", "-q", "--orphan", "other")
    commit(repo, "demo-app/app.py", "x\n", "unrelated")
    git(repo, "tag", "-f", "demo-base", "HEAD")
    git(repo, "checkout", "-q", "main")

    result = run_reset(repo)

    assert result.returncode == 1
    assert "does not contain demo-base" in result.stderr
