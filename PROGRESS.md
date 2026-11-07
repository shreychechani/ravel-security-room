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
- No `gh` login: the owner chose plain git + a fine-grained token instead of authorizing GitHub CLI.

**Next**
- Install Docker Desktop (the owner), then Phase 3: Switch Console + verify the template with switch-docs.

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

- Step 2 done by the owner: Console installed, local server running ("Running locally"), signed in as Admin,
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
  `~/.switch/agents/localhost-52120/sec-triager` (empty, not a git repo, created when the
  agent was added). Either the Directory field was not set or the managed-agent move dropped it. Not fixed on
  purpose: the right directory is a design decision (see Open 6).
- Nothing else blocking. The 8080 move (C2) is still harmless, but its "Switch uses 8000" reason applies only to the
  docker-compose self-host.

**Next ([OWNER], click-by-click given in chat)**
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
   *builder's* rulebook ("stop after each phase, wait for the owner"). Claude Code also reads CLAUDE.md in parent
   directories. Decide: separate clone/worktree for the agents without `CLAUDE.md`, or not. Note the default
   directory name contains the api port (`localhost-52120`), so it may change if ports change (Open 5).
7. Phase 3 template step needs the checks in Open 1–6 answered before `switch/security-room.template.yaml`
   is rewritten.

## Phase 4 — Ravel side (Nov 5) 🟡 verified Ravel, code not started

**Done**
- Read `github.com/shreychechani/Ravel` (public; phases 0–4 built). Installed it with `uv sync` in a
  scratch clone and ran it on `demo-app` (< 1 s):
  B608 `search()` **reachable** (path `search_view → search`), B307 and B506 **unreachable**, plus 2× B101
  (`assert` in tests, unreachable; the adapter will ignore `tests/`).
- `who calls process_payment` is answerable from `graph_view.edges` → `checkout_view`, `retry_job`.
- Fix proof tested on a patched scratch copy (parameterized query): B608 gone, 0 reachable, pytest 2/2.
  `main` untouched.
- Decisions (Opus), recorded in `docs/ARCHITECTURE.md` §7: D2 verify rule, D3 graph-built wiki
  (`ravel summarize` without an LLM key returns placeholder text), D4 Ravel stays a separate repo via `RAVEL_DIR`.
- Team handoff: `docs/HANDOFF.md` (status, setup, task board T1–T9, open questions, rules),
  `docs/ARCHITECTURE.md`, `AGENTS.md`; pointer notes at the top of `CLAUDE.md` and `README.md`.
  `CLAUDE.md`/`AGENTS.md` tell Switch room agents to ignore the builder rules (most of Open 6).
- `.env.example` rewritten: `SWITCH_URL` + registration/agent keys + `RAVEL_DIR`; removed the
  made-up `RAVEL_*_CMD` lines (those Ravel commands don't exist).

**Broken / missing**
- Ravel has no `LICENSE` file (pyproject says MIT); needed so judges can use it (T9, the owner).
- Ravel's entry points don't include the route URL; the adapter reads `@app.route` itself.

**Next**
- T1/T1b/T2 (adapter Ravel side, wiki cache, tests). Can run in parallel with T3 unit part, T4, T8.

## Phase 3, step 6 — Switch template + agent instructions (Nov 5) ✅ written, import test pending

**Done**
- `switch/security-room.template.yaml` rewritten against TEMPLATES.md (version 1 group): params
  `security_owner` (user), `repo_dir` (directory), `bridge`, `provider`, `location`; agents sec-triager
  (own empty folder, addressing anyone) and sec-fixer (repo clone, owner-agents, Auto mode on, Bypass off);
  rooms `security-intake` (room instructions + `triage-playbook` room document + kickoff) and
  `security-ledger`; link between them. Parsed and checked: all placeholders declared, no agent field
  missing, only `ravel` and `sec-scanner` must pre-exist.
- Final instructions: triage flow, ravel commands, fix-room naming `fix-<kind>-<function>`, ledger
  formats, the approval gate (only `@sec-fixer approved` from the security owner's human account).
- Found and fixed: agents wake only when mentioned, so approval is `@sec-fixer approved` and every ravel
  reply must start with `@<asker>` (reply contract in ARCHITECTURE §6, now part of T1).
- Decisions D8–D12 in `docs/ARCHITECTURE.md`; HANDOFF has import steps and the remaining questions.

**Next**
- Import test needs T3 (register ravel + sec-scanner). Delete the Phase 3 test agent/room first.

## Phase 4 — T1 + T1b, Ravel side of the adapter (Nov 5) ✅

**Done**
- `ravel_adapter/config.py`: stdlib `.env` reader; env vars win; relative paths resolve from the repo root.
- `ravel_adapter/ravel.py`: `check`, `verify`, `who calls`, `wiki`, `attach wiki`, `help`. One Ravel run per
  command (`uv run --project $RAVEL_DIR ravel scan … --json`), replies follow the ARCHITECTURE §6 contract
  (start with `@<asker>`), `tests/` findings ignored, route URLs read from `@app.route`. `handle()` never raises.
- `verify` scans the branch in a temporary `git worktree` (removed afterwards; checkout never moves),
  rejects branch names that could be git options, and compares against the current branch (rule D2).
- Wiki pages are built from the call graph (app code only, no tests or library calls); committed fallback
  pages in `ravel_adapter/wiki_cache/` (`python ravel_adapter/ravel.py --build-wiki`).
- `adapter.py` is now the entry point: local test mode; the Switch connection is T3. Old SSE code removed.
- Acceptance (no Switch): check app.py:search → 🔴 REACHABLE, Path GET /api/search → search_view() → search();
  eval_expr and parse → 🟢 UNREACHABLE; who calls process_payment → checkout_view, retry_job; wiki app OK.
  verify on a scratch clone: real fix → ✅ FIX VERIFIED; unchanged branch → ❌ STILL REACHABLE; missing
  branch → clean error. `main` still 3 findings, pytest 1 fail / 1 pass.

**Next**
- T2 (unit tests for ravel.py), T3 (Switch connection: register, WebSocket loop, send, room documents).

## Phase 5 — T3, Switch side of the adapter (Nov 5) ✅ live in Mattermost

**Done**
- `ravel_adapter/switch_client.py`: WebSocket in (`/agents/{id}/connection/ws`, scope=all, filter=addressed),
  pong first on every ping, addressed messages handed to a 2-thread pool, cursor saved after submit,
  resume with `start_from` + `expected_generation`, reconnect backoff 1–30 s (reset after 60 s healthy), stop on
  `taken_over`, `closed`, `refused`, close codes 4400/4401/4403/4409 and handshake 401/403/404.
  HTTP out: `POST /agents/{id}/message`; `attach wiki` calls `connect_to_room` then `create_room_document`
  (or `update_room_document` if the page exists), falling back to posting the page.
- `ravel_adapter/register.py`: registers `ravel` (always_on, addressing anyone) or `sec-scanner`
  (session_passive), writes id + key into `.env` (mode 600); 409 → explains, `--overwrite` only on request.
- `adapter.py` with no arguments now serves; `ravel_adapter/tests/test_switch_client.py`: 10 fake-frame tests pass.
- `websocket-client==1.9.2` added to requirements (approved Nov 4, PLAN C1).
- Switch ports unchanged since Nov 4 (api 52120): ports survived at least a Console restart (Q4, partly).

**Live test (Nov 5)**
- Console 0.40.1 with a server on this Mac has **no Gateway web page and no registration-key screen**
  (switch-buddy confirmed; a settings page is coming in a later release). Workaround:
  `ravel_adapter/registration_key.py` logs in to the Gateway API (`/gateway/auth/login`) and calls
  `POST /gateway/api-keys`. The admin email/password come from the running `switch_core` process's
  environment; the owner ran that step in their own terminal, so the password never reached chat or logs.
- `config.py`: with no `SWITCH_URL`, read the API port from Console's `ports.json` (was a wrong 8000 default).
- Registered `ravel` and `sec-scanner`. Setting addressing with the agent's own key returned **403**;
  switch-buddy set ravel to `anyone` and added it to `#security-intake`.
- `@ravel check app.py:search` in Mattermost → correct 🔴 REACHABLE reply in 1.5 s. ✅ Phase 5 done.
- Real payload: `sender_name` is the plain Mattermost username (`user`), `sender_role: "owner"`; so `@user` replies are right.
- Restart resumed from the saved cursor with no duplicate reply.
- `create_room_document` has **no room_id**: it writes to "the connected room". Fixed `attach_document`
  (connect_to_room first; required fields name, description, instructions, content).

**Next**
- Live test of `@ravel attach wiki app` and `@ravel who calls process_payment`.
- `ravel_adapter/README.md` (plain-language explainer). Then T6 import test.

## Phase 6 prep — T2, T4, T5 merged from teammates (Nov 6)

**Done**
- Pulled PRs #1–#3: `test_handle.py` (T2), `reset_demo.sh` + `demo-base` tag (T4), `post_findings.py` (T5).
  106 adapter tests pass; scan = 3 findings; demo pytest 1 fail / 1 pass; post_findings dry run prints 3 lines.
- Fix: `reset_demo.sh` ran `git reset --hard demo-base` with the tag behind `main`, which would have dropped
  the merged T2/T4/T5 commits. It now refuses when there are uncommitted changes outside `demo-app/`, when
  `main` doesn't contain the tag, or when `main` changed files outside `demo-app/` since the tag; it tells you to
  re-tag. It no longer deletes `.ravel_state.json`. Real-run tests in throwaway repos (fix undone, fix branches
  deleted, idempotent, three refusals). Checked on a scratch clone: refuses today, works after re-tagging.
- Fix: `post_findings.py` matched only a room named `security-intake`; Switch names adopted channels
  `Mattermost: security-intake`. Now both match (test added).

**Next**
- Owner: re-tag `demo-base` on the latest `main` and push the tag. Then T6 import test.

## Phase 6 — T6 import + dry run 1 (Nov 6) ✅ full flow ran end to end, with fixes

**Done**
- Template imported (after adding `instructions` to the room document). Agents and rooms created.
- Dry run 1: 3 findings posted → sec-triager checked all 3 with ravel → 2 dismissed → `#fix-sqli-search`
  opened, wiki attached → sec-fixer fixed on `fix/sqli-search`, pytest 2 passed → ravel ✅ FIX VERIFIED →
  owner typed `@sec-fixer approved` → merged (`b596b33`) → ledger ✅ line. Then `reset_demo.sh` restored
  3 findings, kept every non-demo commit, deleted the fix branch.

**Broke, and fixed**
- sec-fixer's folder came out doubled (`<repo>/Users/.../<repo>`), so it never started. Fixed by hand on
  its page (managed agents can change Directory); template hint now says use **Choose…**.
- `verify` scanned the current checkout as "before"; sec-fixer had the fix branch checked out → ⚪ UNKNOWN.
  Now "before" = `git merge-base main <branch>`, both sides in temporary worktrees. Ravel now runs from
  its own worktree of `main` so sec-fixer's branch switches can't touch its code.
- **Approval gate not wired:** version 1 left `{security_owner}` literal in both agents' instructions.
  Template rewritten in **version 2** (placeholders filled everywhere, per the server's template guide);
  security owner = `{$creator}` (the person who runs it). Server-side `save_template` check: 0 warnings.
  Room document dropped (v2 rooms have no `docs:`); the playbook is in the room instructions instead.
- Ravel answered a message that only mentioned it mid-sentence; now only messages starting with `@ravel`
  are commands, and only the first line is read. sec-triager told to send one recipient per message.
- `reset_demo.sh` wasn't executable in git; fixed.

**Open**
- Ravel posts as "admin" in Mattermost (no bot account for an API-registered agent?). Asking switch-buddy.

**Next**
- Owner: delete agents + rooms + old template, import v2, check the kickoff names the owner. Dry run 2.

## Merge PRs #4–#8 + Phase 8 drafts (Nov 7)

**Done**
- Merged teammates' PRs #4–#8 (cross-platform `config.py`, `scan.py`, `reset_demo.py`,
  `simulate_workflow.py`, `docs/SWITCH_SETUP.md`, `validate_template.py`). No conflicts.
  135 adapter tests pass; scan = 3 findings; simulator 26/26.
- Fix: `validate_template.py` checked the old v1 layout and failed on our v2 template. Rewritten for
  v2 (typed resources, references, resource keys never in text).
- Fix: `reset_demo.py` ignored its arguments, so `--help` ran a real reset (it deleted `fix/sqli-search`;
  restored from `b931a94`). It now parses arguments first.
- `docs/SWITCH_SETUP.md` §4–5 updated to the v2 import (field names, no room document, kickoff check).
- Drafts: `README.md` rewrite (pitch, How Switch is used, Mermaid diagram, two-part quickstart,
  walkthrough, limits), `docs/BLOG.md`, `docs/VIDEO_SCRIPT.md`.

**Open**
- README placeholders: demo GIF (`docs/demo.gif`), video link, Discord confirmation (after T7).
- Ravel posts as "admin" in Mattermost (still asking switch-buddy).

**Next**
- Owner: push, then `git push -f origin demo-base`. Finish dry run 2, then dry run 3; T7 Discord; record.
- Fresh-clone check of the README quickstart.
