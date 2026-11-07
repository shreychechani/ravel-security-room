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
        bad_yaml.write_text("version: 2\nparams:\n  - incomplete: [")
        ok, errors = validate_template(bad_yaml)
        assert ok is False
        assert any("syntax" in e.lower() for e in errors)

    def test_missing_required_agent_fields(self, tmp_path):
        bad = tmp_path / "bad_agent.yaml"
        bad.write_text("""
version: 2
params: {}
resources:
  test_room: {type: room, name: test, bridge: Discord}
  test_agent:
    type: agent
    name: test-agent
    provider: claude
    # missing directory, instructions
""")
        ok, errors = validate_template(bad)
        assert ok is False
        assert any("missing required field" in e for e in errors)

    def test_v1_template_is_rejected(self, tmp_path):
        old = tmp_path / "old.yaml"
        old.write_text("version: 1\nparams: {}\nagents: []\nrooms: []\n")
        ok, errors = validate_template(old)
        assert ok is False
        assert any("version: 2" in e for e in errors)

    def test_undeclared_placeholder(self, tmp_path):
        bad = tmp_path / "placeholder.yaml"
        bad.write_text("""
version: 2
params: {}
resources:
  a_room: {type: room, name: r, bridge: "{bridge}"}
""")
        ok, errors = validate_template(bad)
        assert ok is False
        assert any("{bridge}" in e for e in errors)

    def test_resource_key_in_text_is_caught(self, tmp_path):
        bad = tmp_path / "key_in_text.yaml"
        bad.write_text("""
version: 2
params: {}
resources:
  intake:
    type: room
    name: security-intake
    bridge: Discord
    instructions: Every finding lands in intake.
  triager:
    type: agent
    name: sec-triager
    provider: claude
    directory: /tmp
    instructions: You triage findings.
""")
        ok, errors = validate_template(bad)
        assert ok is False
        assert any("'intake' appears in intake.instructions" in e for e in errors)
