"""Unit tests for template validation and Switch configuration."""
import pytest
from pathlib import Path
from scripts.validate_template import validate_template

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_FILE = ROOT / "switch" / "security-room.template.yaml"


class TestTemplateValidation:
    def test_security_room_template_passes_validation(self):
        ok, errors = validate_template(TEMPLATE_FILE)
        assert ok is True, f"Template validation failed with errors: {errors}"
        assert len(errors) == 0

    def test_missing_file_reports_error(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        ok, errors = validate_template(missing)
        assert ok is False
        assert any("not found" in e for e in errors)

    def test_invalid_yaml_reports_error(self, tmp_path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("version: 1\nparams:\n  - incomplete: [")
        ok, errors = validate_template(bad_yaml)
        assert ok is False
        assert any("syntax" in e.lower() for e in errors)

    def test_missing_required_agent_fields(self, tmp_path):
        bad = tmp_path / "bad_agent.yaml"
        bad.write_text("""
version: 1
params: {}
group: {name: "Test"}
rooms: [{name: "test", bridge: "discord"}]
agents:
  - name: test-agent
    provider: claude
    # missing location, directory, instructions
""")
        ok, errors = validate_template(bad)
        assert ok is False
        assert any("missing required field" in e for e in errors)
