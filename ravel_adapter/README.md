# ravel_adapter: Ravel as a Switch agent

This folder turns [Ravel](https://github.com/shreychechani/Ravel), a command-line tool that
maps a Python codebase, into an agent you can talk to in team chat. In any Switch room it is
in, `@ravel` answers questions with proof taken from the code's call graph, not with an AI's guess.

## What you can ask it

| You type | Ravel answers |
| --- | --- |
| `@ravel check app.py:search` | 🔴 REACHABLE or 🟢 UNREACHABLE, the severity, and the call path from a web route, e.g. `GET /api/search → search_view() → search()` |
| `@ravel verify fix/sqli-search search` | ✅ FIX VERIFIED or ❌ STILL REACHABLE, by scanning the fix branch, plus who calls the function |
| `@ravel who calls process_payment` | Every function that calls it |
| `@ravel wiki payments` | A short page about the module: functions, routes, callers, open findings |
| `@ravel attach wiki app` | The same page, saved as a document in the room, so every agent there can read it |
| `@ravel help` | This list |

Every reply starts with `@<whoever asked>`. In Switch, agents only wake up when mentioned,
so this is what lets sec-triager and sec-fixer act on the answer.

## How it works

```
chat message ──► Switch ──WebSocket──► switch_client.py ──► ravel.py ──► Ravel CLI (scan)
                                                                │
chat reply   ◄── Switch ◄────HTTP──── switch_client.py ◄───────┘
```

1. **Listening (WebSocket in).** `switch_client.py` keeps one WebSocket open to the Switch
   server and receives only messages that mention ravel. Switch sends a ping every 2 seconds;
   the client answers at once, or Switch drops the connection after 6.
2. **Working.** Each request runs on a small thread pool, so a slow scan never delays a ping.
   `ravel.py` runs `ravel scan` on the demo app (under 1 second), reads its JSON, and writes the
   short chat answer. For `verify` it checks out the branch in a temporary git worktree, scans
   it, and removes the worktree; your working copy is never touched.
3. **Answering (HTTP out).** The reply goes back with `POST /agents/{id}/message`. For
   `attach wiki` it first joins the room (`connect_to_room`), then saves the page with
   `create_room_document`, or updates it if the room already has one.
4. **Surviving drops.** The client saves its connection id and its position in the event
   stream in `.ravel_state.json`. After a drop or a restart it resumes from there, so nothing is
   missed and nothing is answered twice. It retries with a growing wait (1 s up to 30 s), and
   stops for good only when Switch says so (wrong key, connection taken over).

| File | Job |
| --- | --- |
| `adapter.py` | Entry point. With text: answer once locally. With no text: connect to Switch |
| `ravel.py` | The commands and the chat formatting (no Switch code) |
| `switch_client.py` | The Switch Agent Protocol: WebSocket in, HTTP out, reconnects |
| `register.py` | Registers the `ravel` and `sec-scanner` agents once and saves their keys in `.env` |
| `registration_key.py` | Creates a registration key when Switch Console has no screen for it |
| `config.py` | Reads settings from the environment and `.env` |
| `wiki_cache/` | Pre-built wiki pages, used if a live scan fails |

## Run it

From the repo root, with `.venv` set up as in the main README:

```bash
# 1. Try it with no Switch at all
.venv/bin/python ravel_adapter/adapter.py "@ravel check app.py:search"

# 2. Get a registration key into .env (once). If Switch Console shows a Gateway page:
#    API Keys -> Create Registration Key, and paste it after SWITCH_REGISTRATION_KEY=.
#    On Console 0.40.1 with a server on your Mac there is no such page; instead run:
.venv/bin/python -m ravel_adapter.registration_key
#    It asks for the Gateway admin email and password (hidden) and saves the key.

# 3. Register the two agents (once). Their ids and keys go into .env.
.venv/bin/python -m ravel_adapter.register ravel
.venv/bin/python -m ravel_adapter.register sec-scanner

# 4. Start Ravel and leave it running
.venv/bin/python ravel_adapter/adapter.py
```

Then let anyone talk to ravel and add it to a room. Ask switch-buddy in Switch Console:
*"set ravel's addressing to anyone and add it to #security-intake"*. Type
`@ravel check app.py:search` in that channel.

## When something goes wrong

| You see | Do this |
| --- | --- |
| `RAVEL_AGENT_ID / RAVEL_AGENT_KEY are empty` | Run step 3 |
| `An agent named 'ravel' already exists` | Its key is in someone's `.env`. If it's lost: `register ravel --overwrite` (the old key stops working) |
| `stopping: handshake refused with HTTP 401` | Wrong key or wrong server. Check `SWITCH_URL` (or leave it empty) |
| `Warning: could not set addressing (HTTP 403)` | Ask switch-buddy to set ravel's addressing to anyone |
| `connection lost …; reconnecting` | Normal after the server restarts; it reconnects by itself |
| ravel is silent in chat | Is `adapter.py` running? Is ravel in that room? Did you type `@ravel`? |
| `Ravel error: …` in chat | Ravel itself failed. Run the same command locally (step 1) to see why |
