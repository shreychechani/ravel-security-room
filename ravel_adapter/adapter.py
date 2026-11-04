"""Ravel agent adapter for Switch.

Switch's Agent Protocol: server-sent events (SSE) in, HTTP out.
This file has two halves:
  1. RAVEL SIDE (done): parse a command, run your Ravel CLI, format a reply.
  2. PROTOCOL SIDE (TODO): connect to Switch, receive messages, send replies.
     Fill in the TODOs from the Agent Protocol docs. The URLs, auth header and
     event field names below are placeholders, not the real protocol.

Commands the agent understands (in any room it is in):
  @ravel check <file>:<function>      reachability verdict + call path
  @ravel verify <branch> <function>   re-check on a fix branch
  @ravel wiki <module>                wiki page for a module
  @ravel who calls <function>         list callers
"""
import json
import os
import shlex
import subprocess

import requests

REPO = os.environ.get("DEMO_REPO_PATH", "./demo-app")
CMDS = {
    "check": os.environ.get("RAVEL_REACH_CMD", "ravel reach --repo {repo} --target {arg}"),
    "wiki": os.environ.get("RAVEL_WIKI_CMD", "ravel wiki --repo {repo} --module {arg}"),
    "callers": os.environ.get("RAVEL_CALLERS_CMD", "ravel callers --repo {repo} --function {arg}"),
}


# ---------- 1. RAVEL SIDE ----------

def run_ravel(kind, arg, repo=REPO):
    """Run a Ravel CLI command safely (no shell) and return its text output."""
    cmd = [part.format(repo=repo, arg=arg) for part in shlex.split(CMDS[kind])]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return f"Ravel error: {result.stderr.strip()[:500]}"
    return result.stdout.strip()


def checkout_branch(branch):
    subprocess.run(["git", "-C", REPO, "fetch", "--all"], capture_output=True)
    subprocess.run(["git", "-C", REPO, "checkout", branch], capture_output=True, check=True)


def handle(text):
    """Turn one chat message into one reply. Returns None if not for ravel."""
    words = text.replace("@ravel", "").strip().split()
    if not words:
        return "Commands: check <file>:<function>, verify <branch> <function>, wiki <module>, who calls <function>"
    verb = words[0].lower()
    if verb == "check" and len(words) >= 2:
        return run_ravel("check", words[1])
    if verb == "verify" and len(words) >= 3:
        checkout_branch(words[1])
        reach = run_ravel("check", words[2])
        callers = run_ravel("callers", words[2])
        return f"Verified on {words[1]}:\n{reach}\nCallers of {words[2]}:\n{callers}"
    if verb == "wiki" and len(words) >= 2:
        return run_ravel("wiki", words[1])
    if verb == "who" and len(words) >= 3 and words[1] == "calls":
        return run_ravel("callers", words[2])
    return "Sorry, I didn't get that. Try: check, verify, wiki, or who calls."


# ---------- 2. PROTOCOL SIDE (TODO from Agent Protocol docs) ----------

EVENTS_URL = os.environ.get("SWITCH_EVENTS_URL")   # TODO: real SSE endpoint
SEND_URL = os.environ.get("SWITCH_SEND_URL")       # TODO: real send endpoint
TOKEN = os.environ.get("SWITCH_AGENT_TOKEN")       # TODO: real auth scheme
HEADERS = {"Authorization": f"Bearer {TOKEN}"}     # TODO: confirm header


def send(room_id, text):
    # TODO: replace the body fields with the protocol's real field names
    requests.post(SEND_URL, headers=HEADERS, json={"room": room_id, "text": text}, timeout=30)


def listen():
    with requests.get(EVENTS_URL, headers=HEADERS, stream=True, timeout=None) as resp:
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            event = json.loads(line[len("data:"):].strip())
            # TODO: replace with the protocol's real event shape
            text, room_id = event.get("text", ""), event.get("room")
            if "@ravel" in text:
                send(room_id, handle(text))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:          # local test without Switch: python adapter.py "@ravel wiki app"
        print(handle(" ".join(sys.argv[1:])))
    else:
        listen()
