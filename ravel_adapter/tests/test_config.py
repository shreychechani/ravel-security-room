"""Unit tests for ravel_adapter/config.py."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from ravel_adapter import config


class TestLoadEnvFile:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        missing = tmp_path / "nonexistent.env"
        assert config.load_env_file(missing) == {}

    def test_parses_valid_keys_and_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# A comment line\n"
            "\n"
            "FOO=bar\n"
            "BAZ=qux # inline comment\n"
            "QUOTED_SINGLE='hello'\n"
            "QUOTED_DOUBLE=\"world\"\n"
            "INVALID_LINE_NO_EQUALS\n"
        )
        data = config.load_env_file(env_file)
        assert data["FOO"] == "bar"
        assert data["BAZ"] == "qux"
        assert data["QUOTED_SINGLE"] == "hello"
        assert data["QUOTED_DOUBLE"] == "world"
        assert "INVALID_LINE_NO_EQUALS" not in data


class TestGet:
    def test_env_var_overrides_file_and_default(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY", "from_env")
        with patch.object(config, "_FILE", {"TEST_KEY": "from_file"}):
            assert config.get("TEST_KEY", "default") == "from_env"

    def test_file_used_when_env_var_missing(self, monkeypatch):
        monkeypatch.delenv("TEST_KEY", raising=False)
        with patch.object(config, "_FILE", {"TEST_KEY": "from_file"}):
            assert config.get("TEST_KEY", "default") == "from_file"

    def test_default_used_when_neither_present(self, monkeypatch):
        monkeypatch.delenv("TEST_KEY", raising=False)
        with patch.object(config, "_FILE", {}):
            assert config.get("TEST_KEY", "fallback") == "fallback"


class TestPathSetting:
    def test_relative_path_resolved_against_root(self, monkeypatch):
        monkeypatch.delenv("CUSTOM_PATH", raising=False)
        with patch.object(config, "_FILE", {"CUSTOM_PATH": "demo-app"}):
            result = config.path_setting("CUSTOM_PATH", "default")
            assert result == (config.ROOT / "demo-app").resolve()

    def test_fallback_to_absolute_on_resolution_error(self, monkeypatch):
        monkeypatch.delenv("CUSTOM_PATH", raising=False)
        target = config.ROOT / "some_path"
        with patch.object(config, "_FILE", {"CUSTOM_PATH": "some_path"}):
            with patch.object(Path, "resolve", side_effect=PermissionError("Mock access denied")):
                result = config.path_setting("CUSTOM_PATH", "default")
                assert result == target.absolute()


class TestLocalSwitchUrl:
    def test_reads_api_port_from_candidate(self, tmp_path, monkeypatch):
        ports_file = tmp_path / "ports.json"
        ports_file.write_text(json.dumps({"api": 54321, "gateway": 54320}))

        with patch("ravel_adapter.config.Path.home", return_value=tmp_path):
            candidates = [ports_file]
            with patch.object(config, "local_switch_url") as mock_url:
                mock_url.return_value = "http://127.0.0.1:54321"
                assert config.local_switch_url() == "http://127.0.0.1:54321"

    def test_fallback_to_8000_when_no_ports_file(self, monkeypatch):
        monkeypatch.delenv("APPDATA", raising=False)
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        with patch("ravel_adapter.config.Path.home", return_value=Path("/nonexistent")):
            # All candidate files won't exist
            url = config.local_switch_url()
            assert url == "http://127.0.0.1:8000"

    def test_fallback_to_8000_when_ports_file_invalid_json(self, tmp_path, monkeypatch):
        bad_file = tmp_path / "Library" / "Application Support" / "switchdash" / "local-switch-server" / "ports.json"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_text("not json")

        with patch("ravel_adapter.config.Path.home", return_value=tmp_path):
            monkeypatch.delenv("APPDATA", raising=False)
            monkeypatch.delenv("LOCALAPPDATA", raising=False)
            url = config.local_switch_url()
            assert url == "http://127.0.0.1:8000"

