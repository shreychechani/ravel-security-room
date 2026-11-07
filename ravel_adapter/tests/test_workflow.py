"""Unit tests for the end-to-end workflow simulator."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIMULATOR = ROOT / "scripts" / "simulate_workflow.py"


class TestWorkflowSimulator:
    def test_simulator_script_exists(self):
        assert SIMULATOR.exists()
        assert SIMULATOR.is_file()

    def test_simulator_runs_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(SIMULATOR)],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, f"Simulator failed:\n{result.stderr}\n{result.stdout}"
        assert "ALL 26 CHECKS PASSED" in result.stdout
        assert "Step 1" in result.stdout
        assert "Step 8" in result.stdout

    def test_simulator_covers_all_eight_steps(self):
        from scripts.simulate_workflow import simulate_workflow
        assert simulate_workflow() == 0
