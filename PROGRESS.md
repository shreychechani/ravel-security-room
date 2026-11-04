# Progress

## Phase 1 — Environment check (Nov 4) ✅

**Done**
- git 2.51.1, Python 3.14.0 (3.11+ required)
- `.venv` created; installed Flask 3.1.3, PyYAML 6.0.3, pytest 9.2.0, bandit 1.9.4, requests 2.34.2
- `./scripts/scan.sh` → exactly 3 findings:
  - B608 `demo-app/app.py:34` SQL injection
  - B307 `demo-app/legacy_utils.py:3` eval
  - B506 `demo-app/vendor/old_parser.py:6` unsafe yaml.load
- `pytest demo-app/tests -q` → 1 passed, 1 failed (`test_search_blocks_sql_injection`, intended)
- App on port 8000 at the time (moved to 8080 in Phase 3): `GET /api/search?q=almo` → `[[1,"almonds"]]`

**Broken / missing**
- Docker is not installed. Switch Console needs it (Phase 3).
- No `gh` login: Shrey chose plain git + a fine-grained token instead of authorizing GitHub CLI.

**Next**
- Install Docker Desktop (Shrey), then Phase 3: Switch Console + verify the template with switch-docs.

## Phase 2 — GitHub (Nov 4) ✅

**Done**
- Repo public: https://github.com/shreychechani/ravel-security-room
- MIT `LICENSE` added
- `switch-docs` MCP fixed: moved to `https://docs.switchagents.ai/mcp`, HTTP transport (not SSE)

**Next**
- Phase 3

## Phase 3 — Switch up and running (Nov 4) ✅ acceptance met; template step (6) waits for Opus

**Done**
- Docker Desktop 29.9.2 installed, daemon running. Note: `docker` is on PATH only in login shells
  (`~/.zprofile`); non-login shells (Claude Code's Bash tool) need `~/.docker/bin/docker`.
- Step 3 (C2): demo app now listens on **8080** (`PORT` env overrides). Verified:
  `curl 127.0.0.1:8080/api/search?q=almo` → `[[1,"almonds"]]`. README and CLAUDE.md updated.
- Re-ran Phase 1 checks after the change: scan = 3 findings (B608, B307, B506); pytest = 1 pass, 1 fail.
- `requirements.txt` pinned to the installed versions; `scan.sh` uses `.venv/bin/bandit` and fails
  loudly instead of printing stale `findings.json`; `.gitignore` covers `.ravel_state.json`, `.ravel-worktrees/`.

- Step 2 done by Shrey: Console installed, local server running ("Running locally"), signed in as Admin,
  switch-buddy powered by Claude Code.
- Step 4 done, **with a correction to PLAN.md**: the Console-run local server does **not** use 8000/3000.
  Console picks free ports and writes them to
  `~/Library/Application Support/switchdash/local-switch-server/ports.json`. This run:
  `{"gateway": 52119, "api": 52120, "mattermost": 52121, "postgres": 52122}`.
  `curl http://127.0.0.1:52120/health` → `{"status":"ok"}` (200). So **`SWITCH_URL=http://127.0.0.1:52120`**.
  `/health` on the Gateway port gives 404, and on the agent-controller/agent-host ports (separate
  Console sidecars) 401, so only the `api` port is the bridge. 8000/3000 are for the docker-compose self-host.
- The server runs natively (`switch_core` 0.31.0 + Postgres); only Mattermost is a Docker container.

- Step 5 done: agent `sec-triager` (Claude Code) created, Mattermost channel `security-intake` made, bot
  `sec-triager` added (that creates the room on Mattermost). `@sec-triager hello, which folder are you working in?`
  → replied after ~15 s ("Starting a session to handle this"). **Phase 3 "done when" is met.**
- Mattermost went down once because Docker Desktop was quit (container exited 0). Fixed with
  `docker start switchdash-local-mattermost-mattermost-1`; it keeps port 52121 (pinned in
  `native/mattermost-compose.yml`). Docker Desktop must stay open for the whole demo.

**Broken / blocked**
- sec-triager's working directory is **not the repo**: it reported
  `/Users/shreychechani/.switch/agents/localhost-52120/sec-triager` (empty, not a git repo, created when the
  agent was added). Either the Directory field was not set or the managed-agent move dropped it. Not fixed on
  purpose: the right directory is a design decision (see Open 6).
- Nothing else blocking. The 8080 move (C2) is still harmless, but its "Switch uses 8000" reason applies only to the
  docker-compose self-host.

**Next ([SHREY], click-by-click given in chat)**
- Step 5: sign in to Mattermost (Home → Messaging apps → Sign-in details…), add `sec-triager` in Your Agents,
  mention it in a Mattermost channel.
- Step 6 is `[OPUS]`: finish the template (§5) and agent instructions (§6).

**Open (for an Opus session; found in the docs, not in PLAN.md)**
1. Console 0.40 (Oct 20, 2026): a Console-run local server now has **agent management on**, and agents
   run on a *managed machine* that keeps running after Console quits. Check template `location`/`directory`
   still apply, and whether `sec-triager`/`sec-fixer` can still see the repo working directory.
2. **Addressing has a fourth option, "Custom rules"** (people, agents, rooms named individually) besides
   Only me / Me and my agents / Anyone (`/switch-rooms/getting-started/agent-settings#choose-who-can-instruct-the-agent`).
   Could make the approval gate stricter than `owner-agents` (§6 layer 1). Confirm it exists in template YAML.
3. New agents created in Console default to **"Me and my agents"** and start with **Auto mode on, Bypass
   permissions off**. Decide Auto mode / Bypass for `sec-fixer` (it merges; bypass would weaken the gate).
4. Docker is now optional for the server, but the **bundled Mattermost needs it**; keep Docker for the dev chat.
5. **Ports are random per Console install** (see Phase 3 Done). PLAN.md §3/§4.1 assume `localhost:8000`; the
   adapter must take `SWITCH_URL` from `.env`, and the README quickstart must tell judges to copy the `api`
   port from `ports.json`. Unknown: do the ports stay the same after the server restarts or the laptop reboots?
   Decide whether `config.py` should fall back to reading `ports.json` when `SWITCH_URL` is unset.
6. **Agent working directory.** Console's managed agents use `~/.switch/agents/<server-host>-<api-port>/<name>`
   unless Directory points elsewhere; a managed agent's Directory is editable on its page (full path;
   `Choose…` only on this computer), and the agent restarts when it changes
   (`/switch-rooms/getting-started/agent-settings#rename-or-move-the-agent`). Two problems to design around:
   (a) `sec-fixer` needs a real git checkout to branch, patch, run pytest and merge; (b) docs say standing
   instructions in the working directory "become its default behavior", and this repo's `CLAUDE.md` is the
   *builder's* rulebook ("stop after each phase, wait for Shrey"). Claude Code also reads CLAUDE.md in parent
   directories. Decide: separate clone/worktree for the agents without `CLAUDE.md`, or not. Note the default
   directory name contains the api port (`localhost-52120`), so it may change if ports change (Open 5).
7. Phase 3 template step needs the checks in Open 1–6 answered before `switch/security-room.template.yaml`
   is rewritten.
