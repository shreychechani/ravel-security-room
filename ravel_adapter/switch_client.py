"""Switch side of the adapter: the Switch Agent Protocol (WebSocket in, HTTP out).

Docs: /switch-rooms/internals/agent-protocol, agent-connection, agent-events.

How it works:
- One WebSocket, opened with the agent's API key, a connection id we keep forever,
  scope=all (every room ravel is in) and filter=addressed (only messages for us).
- The server sends {"type": "ping"} every 2 s; we answer {"type": "pong", "cursor": n}
  at once, or it drops us after 6 s. So the socket thread never runs Ravel itself:
  addressed messages go to a small thread pool, which runs the command and posts the reply.
- After a drop we reconnect from our saved cursor, with backoff, unless the server says stop.
"""
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode

import requests
import websocket

log = logging.getLogger("ravel")

# What to do after the socket closes (close codes from the agent-connection docs).
STOP_CODES = {4400: "bad connection parameters (a bug)", 4401: "invalid API key",
              4403: "a room can't be served", 4409: "taken over or conflicting connection"}
RECONNECT_EVICTIONS = {"heartbeat_lapsed", "no_stream", "unfenced", "connection_error"}
BACKOFF = [1, 2, 4, 8, 16, 30]
HEALTHY_AFTER = 60   # seconds connected before the backoff resets


class Stop(Exception):
    """The server told us not to reconnect."""


class State:
    """connection_id, cursor and generation, kept in .ravel_state.json across restarts."""

    def __init__(self, path):
        self.path = Path(path)
        data = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.connection_id = data.get("connection_id") or str(uuid.uuid4())
        self.cursor = data.get("cursor")          # last event sequence we handled
        self.generation = data.get("generation")
        self.save()

    def save(self):
        self.path.write_text(json.dumps({"connection_id": self.connection_id,
                                         "cursor": self.cursor,
                                         "generation": self.generation}))


class SwitchClient:
    def __init__(self, base_url, agent_id, api_key, handler, state_path, names=("ravel",)):
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.api_key = api_key
        self.handler = handler          # (body, sender_name) -> ravel.Reply
        self.names = names
        self.state = State(state_path)
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.logged_raw = False

    # ---------- HTTP out ----------

    def _headers(self, with_connection=False):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if with_connection:
            headers["X-Switch-Connection-Id"] = self.state.connection_id
        return headers

    def send(self, room_id, text):
        """Post a message. Needs no connection (POST /agents/{id}/message)."""
        resp = requests.post(f"{self.base_url}/agents/{self.agent_id}/message",
                             headers=self._headers(), json={"room_id": room_id, "content": text},
                             timeout=30)
        resp.raise_for_status()

    def call_op(self, name, args):
        """POST /agents/{id}/ops/{name} with the arguments unwrapped."""
        resp = requests.post(f"{self.base_url}/agents/{self.agent_id}/ops/{name}",
                             headers=self._headers(with_connection=True), json=args, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result")

    def attach_document(self, room_id, name, content):
        """Save a page as a room document. Returns None, or the reason it couldn't.

        Room documents belong to "the connected room", so we connect to the room first
        (connect_to_room). A name is unique per room: attaching again updates the page.
        """
        fields = {"description": f"Ravel wiki page: {name.removeprefix('wiki-')}",
                  "instructions": "Ravel's map of this module: what it does, who calls each "
                                  "function, which functions a route reaches, and open findings. "
                                  "Read it before changing the module.",
                  "content": content}
        try:
            room = self.call_op("connect_to_room", {"room_id": room_id,
                                                    "include_general_instructions": False}) or {}
            old = next((d for d in room.get("documents") or [] if d.get("name") == name), None)
            if old:
                self.call_op("update_room_document",
                             {"document_id": old.get("document_id") or old.get("id"), **fields})
            else:
                self.call_op("create_room_document", {"name": name, **fields})
        except requests.HTTPError as err:
            return f"HTTP {err.response.status_code} {err.response.text[:120]}"
        return None

    # ---------- the work, on a pool thread ----------

    def answer(self, room_id, sender_name, body):
        started = time.monotonic()
        try:
            reply = self.handler(body, sender_name)
            text = reply.text
            if reply.document:
                name, content = reply.document
                problem = self.attach_document(room_id, name, content)
                if problem:   # fallback from PLAN §4.4: post the page as a message
                    text = f"@{sender_name} {content}\n(couldn't attach as a room document: {problem})"
            self.send(room_id, text)
            log.info("replied in %.1fs", time.monotonic() - started)
        except Exception as err:   # never let one command kill the worker
            log.error("could not answer: %s", err)

    # ---------- WebSocket in ----------

    def ws_url(self):
        query = {"connection_id": self.state.connection_id, "scope": "all", "filter": "addressed",
                 "start_from": self.state.cursor if self.state.cursor is not None else "head",
                 "client": "ravel-adapter", "client_version": "0.1"}
        if self.state.generation is not None:
            query["expected_generation"] = self.state.generation
        base = self.base_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        return f"{base}/agents/{self.agent_id}/connection/ws?{urlencode(query)}"

    def on_frame(self, frame, send_frame):
        """Handle one decoded frame. Raises Stop to end for good, ConnectionError to reconnect."""
        kind = frame.get("type") or frame.get("event")

        if kind == "ping":   # first, always: a late pong gets us evicted
            send_frame({"type": "pong", "cursor": self.state.cursor or 0})
            return
        if kind == "connection_state":
            self.state.generation = frame.get("generation")
            if frame.get("cursor") is not None:
                self.state.cursor = frame["cursor"]
            self.state.save()
            log.info("connected · %d rooms · cursor %s", len(frame.get("rooms") or []),
                     self.state.cursor)
            return
        if kind == "gap":
            self.state.cursor = frame.get("resumed_at", self.state.cursor)
            self.state.save()
            log.warning("gap in events (%s); resuming at %s", frame.get("reason"), self.state.cursor)
            return
        if kind == "evicted":
            code = frame.get("code")
            if code in RECONNECT_EVICTIONS:
                raise ConnectionError(f"evicted: {code}")
            raise Stop(f"evicted: {code} ({frame.get('reason')})")
        if kind == "refused":
            raise Stop(f"refused: {frame.get('status')} {frame.get('detail')}")
        if frame.get("event") == "message":
            self.on_message(frame)

    def on_message(self, frame):
        data = frame.get("data", {})
        payload = data.get("payload", {})
        if not self.logged_raw:   # once, to see the real field values (PLAN Phase 5.5)
            log.info("first message payload: %s", json.dumps(payload)[:500])
            self.logged_raw = True
        sender_name = payload.get("sender_name") or "someone"
        if payload.get("addressed") and sender_name.lower() not in self.names:
            body = payload.get("body", "")
            log.info("%s %s: %s", data.get("room_id", "?")[:8], sender_name, body[:60])
            self.pool.submit(self.answer, data.get("room_id"), sender_name, body)
        # Advance after submitting, so a slow command never holds up pings.
        seq = frame.get("id", data.get("sequence"))
        if seq is not None:
            self.state.cursor = seq
            self.state.save()

    def run_once(self):
        """One connection, until it drops (always ends with an exception)."""
        try:
            ws = websocket.create_connection(self.ws_url(), timeout=15,
                                             header=[f"Authorization: Bearer {self.api_key}"])
        except websocket.WebSocketBadStatusException as err:
            if err.status_code in (401, 403, 404):   # wrong key or wrong URL: retrying won't help
                raise Stop(f"handshake refused with HTTP {err.status_code}; check SWITCH_URL and the key") from None
            raise
        try:
            while True:   # 15 s without any frame (pings come every 2 s) raises a timeout
                opcode, data = ws.recv_data(control_frame=True)
                if opcode == websocket.ABNF.OPCODE_CLOSE:
                    code = int.from_bytes(data[:2], "big") if len(data) >= 2 else 1000
                    if code in STOP_CODES:
                        raise Stop(f"closed {code}: {STOP_CODES[code]}")
                    raise ConnectionError(f"closed {code}")
                if opcode == websocket.ABNF.OPCODE_TEXT:
                    self.on_frame(json.loads(data), lambda f: ws.send(json.dumps(f)))
        finally:
            ws.close()

    def run_forever(self):
        attempt = 0
        while True:
            started = time.monotonic()
            try:
                self.run_once()
            except Stop as err:
                log.error("stopping: %s", err)
                return
            except (ConnectionError, OSError, websocket.WebSocketException) as err:
                if time.monotonic() - started > HEALTHY_AFTER:
                    attempt = 0
                wait = BACKOFF[min(attempt, len(BACKOFF) - 1)]
                attempt += 1
                log.warning("connection lost (%s); reconnecting in %ss", err, wait)
                time.sleep(wait)
