"""Unit tests for scripts/post_findings.py."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.post_findings import (
    find_enclosing_function,
    format_finding_message,
    get_room_id,
    load_findings,
    post_all_findings,
    post_message,
)


class TestPostFindingsFormatting:
    def test_find_enclosing_function_in_app(self):
        # Line 34 in demo-app/app.py is inside search()
        fn = find_enclosing_function("demo-app/app.py", 34)
        assert fn == "search"

    def test_find_enclosing_function_nonexistent(self):
        fn = find_enclosing_function("demo-app/nonexistent.py", 10)
        assert fn == "unknown"

    def test_format_finding_message(self):
        finding = {
            "test_id": "B608",
            "filename": "demo-app/app.py",
            "line_number": 34,
            "issue_text": "Possible SQL injection vector",
        }
        msg = format_finding_message(finding)
        assert msg == "@sec-triager New finding B608 in demo-app/app.py:34 (search): Possible SQL injection vector."

    def test_format_finding_message_adds_demo_app_prefix(self):
        finding = {
            "test_id": "B307",
            "filename": "./legacy_utils.py",
            "line_number": 3,
            "issue_text": "Use of eval detected",
        }
        msg = format_finding_message(finding)
        assert msg.startswith("@sec-triager New finding B307 in demo-app/legacy_utils.py:3 (eval_expr):")


class TestPostFindingsLoadingAndPosting:
    def test_load_findings_filters_tests(self, tmp_path):
        sample = {
            "results": [
                {"test_id": "B608", "filename": "demo-app/app.py", "line_number": 34},
                {"test_id": "B101", "filename": "demo-app/tests/test_app.py", "line_number": 12},
            ]
        }
        findings_file = tmp_path / "findings.json"
        findings_file.write_text(json.dumps(sample))

        findings = load_findings(findings_file)
        assert len(findings) == 1
        assert findings[0]["test_id"] == "B608"

    @patch("requests.post")
    def test_get_room_id_finds_match(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"result": [
                {"name": "general", "id": "room-1"},
                {"name": "#security-intake", "id": "room-2"},
            ]}
        )
        room_id = get_room_id("http://fake", "agent-1", "key", "security-intake")
        assert room_id == "room-2"

    @patch("requests.post")
    def test_get_room_id_matches_adopted_channel_name(self, mock_post):
        # Real list_rooms result for a room Switch adopted from a Mattermost channel
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"result": [
                {"room_id": "room-0", "name": "Mattermost: security-intake-old"},
                {"room_id": "room-3", "name": "Mattermost: security-intake"},
            ]}
        )
        assert get_room_id("http://fake", "agent-1", "key", "security-intake") == "room-3"

    @patch("requests.post")
    def test_get_room_id_not_found_raises(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"result": [{"name": "general", "id": "room-1"}]}
        )
        with pytest.raises(ValueError, match="Room 'security-intake' not found"):
            get_room_id("http://fake", "agent-1", "key", "security-intake")

    @patch("requests.post")
    def test_get_room_id_refuses_to_guess_between_apps(self, mock_post):
        rooms = {"result": [
            {"room_id": "room-m", "name": "Mattermost: security-intake"},
            {"room_id": "room-d", "name": "Discord: security-intake"},
        ]}
        mock_post.return_value = MagicMock(status_code=200, json=lambda: rooms)
        with pytest.raises(ValueError, match="Several rooms match"):
            get_room_id("http://fake", "agent-1", "key", "security-intake")
        # The full name picks one
        assert get_room_id("http://fake", "agent-1", "key", "Discord: security-intake") == "room-d"

    @patch("requests.post")
    def test_post_message_sends_payload(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        post_message("http://fake", "agent-1", "key", "room-123", "Hello room")
        mock_post.assert_called_once_with(
            "http://fake/agents/agent-1/message",
            headers={"Authorization": "Bearer key"},
            json={"room_id": "room-123", "content": "Hello room"},
            timeout=15,
        )

    def test_post_all_findings_dry_run(self, tmp_path):
        sample = {
            "results": [
                {"test_id": "B608", "filename": "demo-app/app.py", "line_number": 34, "issue_text": "SQLi"},
            ]
        }
        findings_file = tmp_path / "findings.json"
        findings_file.write_text(json.dumps(sample))

        messages = post_all_findings(dry_run=True, findings_path=findings_file)
        assert len(messages) == 1
        assert "@sec-triager New finding B608" in messages[0]
