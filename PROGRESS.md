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

## Phase 3 — Switch up and running (Nov 4) ⏳ in progress

**Done**
- Docker Desktop 29.9.2 installed, daemon running. Note: `docker` is on PATH only in login shells
  (`~/.zprofile`); non-login shells (Claude Code's Bash tool) need `~/.docker/bin/docker`.
- Step 3 (C2): demo app now listens on **8080** (`PORT` env overrides). Verified:
  `curl 127.0.0.1:8080/api/search?q=almo` → `[[1,"almonds"]]`. README and CLAUDE.md updated.
- Re-ran Phase 1 checks after the change: scan = 3 findings (B608, B307, B506); pytest = 1 pass, 1 fail.
- `requirements.txt` pinned to the installed versions; `scan.sh` uses `.venv/bin/bandit` and fails
  loudly instead of printing stale `findings.json`; `.gitignore` covers `.ravel_state.json`, `.ravel-worktrees/`.

**Broken / blocked**
- Step 4 (`curl localhost:8000/health`): nothing listens on 8000 yet. Needs Shrey's Console server (step 2).

**Next ([SHREY], click-by-click given in chat)**
- Steps 2 and 5: install Console, start the local server, sign in to Mattermost, add `sec-triager`.
- Then `curl http://localhost:8000/health` to confirm the bridge base URL (step 4).
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
