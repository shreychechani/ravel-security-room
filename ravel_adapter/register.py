"""Register a custom agent with Switch, once, and save its id + key in .env.

    python -m ravel_adapter.register ravel         # the Ravel agent (answers anyone)
    python -m ravel_adapter.register sec-scanner   # the identity scripts post findings as

Needs SWITCH_URL and SWITCH_REGISTRATION_KEY in .env
(Gateway → API Keys → Create Registration Key). Docs: /switch-rooms/internals/agent-protocol.
The API key is shown only once, so it goes straight into .env (never committed).
"""
import sys

import requests

from . import config

AGENTS = {
    "ravel": {
        "env": ("RAVEL_AGENT_ID", "RAVEL_AGENT_KEY"),
        "display_name": "ravel",
        "description": "Reachability proof for security findings: check, verify, who calls, wiki",
        "connection_model": "always_on",        # a long-running process, reachable in any room
        "addressing": "anyone",                 # Ask Ravel is for every developer
    },
    "sec-scanner": {
        "env": ("SCANNER_AGENT_ID", "SCANNER_AGENT_KEY"),
        "display_name": "sec-scanner",
        "description": "Posts scanner findings into #security-intake",
        "connection_model": "session_passive",  # only posts; nothing listens for it
        "addressing": None,                     # keep the default: answers only its owner
    },
}


def save_to_env(updates):
    """Set KEY=value lines in .env (created from .env.example if missing)."""
    env = config.ROOT / ".env"
    if not env.exists():
        env.write_text((config.ROOT / ".env.example").read_text())
    lines = env.read_text().splitlines()
    for key, value in updates.items():
        for i, line in enumerate(lines):
            if line.split("=", 1)[0].strip() == key:
                lines[i] = f"{key}={value}"
                break
        else:
            lines.append(f"{key}={value}")
    env.write_text("\n".join(lines) + "\n")
    env.chmod(0o600)


def register(name, overwrite=False):
    spec = AGENTS[name]
    if not config.SWITCH_REGISTRATION_KEY:
        sys.exit("SWITCH_REGISTRATION_KEY is empty in .env (Gateway → API Keys → Create Registration Key).")

    body = {
        "name": name,
        "display_name": spec["display_name"],
        "description": spec["description"],
        "connector_type": "ravel-security-room",
        "integration_profile": {
            "connection_model": spec["connection_model"],
            "message_exchange": True,
            "pre_invocation_mediation": [],
            "post_invocation_mediation": [],
            "event_reporting": [],
        },
    }
    if overwrite:
        body["overwrite"] = True
    resp = requests.post(f"{config.SWITCH_URL}/agents", json=body, timeout=30,
                         headers={"Authorization": f"Bearer {config.SWITCH_REGISTRATION_KEY}"})
    if resp.status_code == 409:
        sys.exit(f"An agent named '{name}' already exists. If its key is lost, re-run with "
                 "--overwrite (this issues a new key and the old one stops working).")
    if not resp.ok:
        sys.exit(f"Registration failed: HTTP {resp.status_code} {resp.text[:200]}")

    agent = resp.json()
    id_key, secret_key = spec["env"]
    save_to_env({id_key: agent["id"], secret_key: agent["api_key"]})
    print(f"Registered '{name}' (id {agent['id']}); id and key saved to .env.")

    if spec["addressing"]:
        resp = requests.post(
            f"{config.SWITCH_URL}/agents/{agent['id']}/ops/update_agent_detail",
            headers={"Authorization": f"Bearer {agent['api_key']}"},
            json={"agent_id": agent["id"], "addressing": spec["addressing"]}, timeout=30)
        if resp.ok:
            print(f"Addressing set to '{spec['addressing']}'.")
        else:
            print(f"Warning: could not set addressing (HTTP {resp.status_code}); "
                  "set it on the agent's page in Switch Console.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--overwrite"]
    if len(args) != 1 or args[0] not in AGENTS:
        sys.exit(f"usage: python -m ravel_adapter.register {{{'|'.join(AGENTS)}}} [--overwrite]")
    register(args[0], overwrite="--overwrite" in sys.argv)
