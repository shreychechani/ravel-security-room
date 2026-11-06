"""Frame handling of the Switch client, with fake frames (no network)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ravel_adapter.switch_client import Stop, SwitchClient  # noqa: E402


class FakePool:
    def __init__(self):
        self.jobs = []

    def submit(self, fn, *args):
        self.jobs.append(args)


@pytest.fixture
def client(tmp_path):
    c = SwitchClient("http://127.0.0.1:9", "agent-1", "secret", handler=None,
                     state_path=tmp_path / "state.json")
    c.pool = FakePool()
    return c


def message(seq, body="@ravel check app.py:search", addressed=True, sender="sec-triager"):
    return {"event": "message", "id": seq,
            "data": {"type": "message", "room_id": "room-1", "sequence": seq,
                     "payload": {"addressed": addressed, "sender": "@switch-agent-x:local",
                                 "sender_name": sender, "body": body}}}


def test_ping_gets_a_pong_with_the_cursor(client):
    sent = []
    client.state.cursor = 41
    client.on_frame({"type": "ping"}, sent.append)
    assert sent == [{"type": "pong", "cursor": 41}]


def test_connection_state_keeps_generation_and_cursor(client, tmp_path):
    client.on_frame({"type": "connection_state", "generation": 3, "cursor": 10, "rooms": ["r"]},
                    lambda f: None)
    saved = json.loads((tmp_path / "state.json").read_text())
    assert (saved["generation"], saved["cursor"]) == (3, 10)


def test_addressed_message_is_queued_and_cursor_advances(client):
    client.on_frame(message(12), lambda f: None)
    assert client.pool.jobs == [("room-1", "sec-triager", "@ravel check app.py:search")]
    assert client.state.cursor == 12


def test_message_not_addressed_is_ignored_but_cursor_advances(client):
    client.on_frame(message(13, addressed=False), lambda f: None)
    assert client.pool.jobs == []
    assert client.state.cursor == 13


def test_own_message_is_ignored(client):
    client.on_frame(message(14, sender="ravel"), lambda f: None)
    assert client.pool.jobs == []


def test_gap_moves_the_cursor(client):
    client.on_frame({"type": "gap", "resumed_at": 99, "reason": "restart"}, lambda f: None)
    assert client.state.cursor == 99


def test_taken_over_stops_for_good(client):
    with pytest.raises(Stop):
        client.on_frame({"type": "evicted", "code": "taken_over"}, lambda f: None)


def test_heartbeat_lapsed_reconnects(client):
    with pytest.raises(ConnectionError):
        client.on_frame({"type": "evicted", "code": "heartbeat_lapsed"}, lambda f: None)


def test_connection_id_survives_a_restart(tmp_path):
    first = SwitchClient("http://x", "a", "k", None, tmp_path / "s.json")
    second = SwitchClient("http://x", "a", "k", None, tmp_path / "s.json")
    assert first.state.connection_id == second.state.connection_id


def test_resume_url_carries_cursor_and_generation(client):
    client.state.cursor, client.state.generation = 7, 2
    url = client.ws_url()
    assert url.startswith("ws://127.0.0.1:9/agents/agent-1/connection/ws?")
    assert "start_from=7" in url and "expected_generation=2" in url and "filter=addressed" in url


def test_mention_further_in_is_not_a_command(client):
    body = "@sec-fixer Ravel's verify is fixed. Please run @ravel verify fix/sqli-search search"
    client.on_frame(message(15, body=body, sender="user"), lambda f: None)
    assert client.pool.jobs == []
    assert client.state.cursor == 15


def test_command_with_trailing_lines_is_still_a_command(client):
    body = "@ravel attach wiki app\n@sec-fixer Fix B608 in demo-app/app.py"
    client.on_frame(message(16, body=body), lambda f: None)
    assert client.pool.jobs == [("room-1", "sec-triager", body)]
