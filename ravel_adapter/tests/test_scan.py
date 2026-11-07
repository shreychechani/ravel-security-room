"""Unit tests for scripts/scan.py and security scanning functionality."""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts import scan

ROOT = Path(__file__).resolve().parents[2]


class TestScanScript:
    def test_scan_script_exists(self):
        script = ROOT / "scripts" / "scan.py"
        assert script.exists()
        assert script.is_file()

    def test_run_scan_produces_baseline_findings(self, tmp_path):
        out_file = tmp_path / "test_findings.json"
        code = scan.run_scan(
            target_dir="demo-app",
            exclude_dir="demo-app/tests",
            output_json=str(out_file),
            quiet=True,
        )
        assert code == 0
        assert out_file.exists()

        data = json.loads(out_file.read_text(encoding="utf-8"))
        results = data.get("results", [])
        rules = [r.get("test_id") for r in results]

        # Baseline demo findings: SQL injection, eval, yaml.load
        assert "B608" in rules
        assert "B307" in rules
        assert "B506" in rules

        # Verify tests are excluded
        for r in results:
            fname = r.get("filename", "").replace("\\", "/")
            assert "demo-app/tests" not in fname
            assert "/tests/" not in fname

    def test_scan_cli_execution(self, tmp_path):
        out_file = tmp_path / "cli_findings.json"
        cmd = [sys.executable, str(ROOT / "scripts" / "scan.py"), "-o", str(out_file), "-q"]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        assert proc.returncode == 0
        assert out_file.exists()

        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert len(data.get("results", [])) == 3

    def test_missing_bandit_returns_error_code(self, tmp_path):
        out_file = tmp_path / "fail.json"
        with patch("scripts.scan.find_bandit", return_value="/nonexistent/bandit"):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                code = scan.run_scan(output_json=str(out_file), quiet=True)
                assert code == 2

    def test_bandit_error_exit_code_propagated(self, tmp_path):
        out_file = tmp_path / "fail.json"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=127, stdout="", stderr="crash"
            )
            code = scan.run_scan(output_json=str(out_file), quiet=True)
            assert code == 127

