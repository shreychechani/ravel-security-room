# PLAN.md — Ravel Security Room build plan

Written Nov 4, 2026 (Day 1) by Opus, after reading the Switch docs at
`https://docs.switchagents.ai/mcp`. `CLAUDE.md` says **what** we build and the rules;
this file says **how**, task by task. **Where the two disagree, this file wins** (§2 lists
every correction).

## 0. How to use this file

- **Model split.** Every task is tagged:
  - `[SONNET]`: well-specified coding. Follow the spec, run the acceptance check, commit.
  - `[OPUS]`: needs judgment (design, debugging an unclear failure, wording agent
    instructions, the pitch). Switch to Opus (`/model`) for these.
  - `[OWNER]`: GUI, accounts or decisions only the project owner can do. Print click-by-click steps and wait.
- **Escalate to Opus** whenever a `[SONNET]` task hits something this plan didn't predict:
  a Switch response that doesn't match §3, a test that fails for an unclear reason, or a
  choice not written down here. Don't guess; write the question in `PROGRESS.md` under "Open".
- **Every Switch fact** still gets checked with the `switch-docs` MCP before code depends on
  it. §3 is a summary with doc paths, not a substitute.
- **After each phase:** update `PROGRESS.md` (done / broken / next), commit locally, stop,
  wait for "continue". The owner pushes (`git push`); there's no `gh` login on the build machine.

## 1. Status (Nov 4)

| Phase | State |
| --- | --- |
| 1 Environment | ✅ Done (Python 3.14, venv, scan = 3 findings, pytest 1 pass / 1 fail, app ok) |
| 2 GitHub | ✅ Done: https://github.com/shreychechani/ravel-security-room (public, MIT) |
| 3 Switch up | ✅ Server + Mattermost up, sec-triager replies. Template/instructions (step 6) still open |
| 4 Ravel side | 🟡 Ravel verified on demo-app (Nov 5); decisions D2–D4 in `docs/ARCHITECTURE.md` §7. Code not started |
| 5–8 | Not started |

**Nov 5 update (Opus):** the live task board is now `docs/HANDOFF.md` §3 (tasks T1–T9, for
teammates too). Where this file and `docs/ARCHITECTURE.md` §6–§8 disagree, ARCHITECTURE wins:
real Ravel commands (`ravel scan --json`, no `reach`/`wiki`/`callers` commands), random Switch
ports (not 8000/3000), the verify rule (D2) and the graph-built wiki (D3).

## 2. Corrections to CLAUDE.md (verified in the docs)

| # | CLAUDE.md / starter says | Reality (doc) | What we do |
| --- | --- | --- | --- |
| C1 | Agent Protocol = "SSE in, HTTP out" | WebSocket in, HTTP out. SSE is deprecated and "will be removed after a transition period" (`/switch-rooms/internals/agent-protocol`) | Adapter uses WebSocket via `websocket-client` (approved by the owner Nov 4) |
| C2 | Demo app on port 8000 | Local Switch stack publishes its API on **8000** and Gateway on **3000** (`/switch-rooms/deploy/self-host`) | Move demo app to **8080** (env `PORT`, default 8080) |
| C3 | Template fields `{provider}`, `{bridge}` just work | Placeholders must be declared under `params:`; every created agent needs `provider`, `location`/`machine` and `directory` (TEMPLATES.md) | Rewrite template, see §5 |
| C4 | Ravel "joins later" | A **room** template stops if any agent it names doesn't exist yet | Register `ravel` + `sec-scanner` **before** importing the template, then list them in the room |
| C5 | `SWITCH_EVENTS_URL` / `SWITCH_SEND_URL` / `SWITCH_AGENT_TOKEN` | One bridge base URL + agent id + agent API key. Registration uses a separate **registration key** | New `.env` keys, see §4.1 |
| C6 | "Set roles so only the owner can approve" | Switch room *roles* are hats agents wear, not human permissions. Who may instruct an agent is its **addressing** setting | Gate = sec-fixer addressing + instructions + a visible refusal, see §6 |
| C7 | `verify` does `git checkout` in the repo | That would move the working tree under sec-fixer mid-demo | `verify` uses a temporary `git worktree`, see §4.4 |

## 3. Switch facts we rely on (summary; verify via switch-docs)

**Registration** (`/switch-rooms/internals/agent-protocol#register-the-agent`)
- `POST {BASE}/agents` with `Authorization: Bearer <registration key>`. The key is created in
  the Gateway → **API Keys** → **Create Registration Key**; its creator owns the agent.
- Body: `name` (`^[a-z0-9][a-z0-9._-]*$`), `description`, `connector_type` (free text),
  `integration_profile: {connection_model, message_exchange, pre_invocation_mediation: [],
  post_invocation_mediation: [], event_reporting: []}`. Optional `display_name`, `overwrite`.
- Response `{id, api_key}`. **The api_key is shown once.** The same name again → 409;
  `overwrite: true` issues a new key and the old one stops working.
- Do NOT use `/agents/register-known`.
- New agents answer **only their owner**. Change with
  `POST /agents/{id}/ops/update_agent_detail` `{"agent_id": id, "addressing": "anyone"}`
  (values: `owner_only`, `owner_and_owner_agents`, `anyone`).

**Finding the base URL:** `GET {BASE}/health` is public. Healthy = right URL; 401 = right
host, wrong path. The bridge URL is usually **not** the Gateway URL (3000). Expect
`http://localhost:8000`, but confirm with `/health`.

**WebSocket** (`/switch-rooms/internals/agent-connection`)
- `GET {BASE→ws}/agents/{id}/connection/ws?connection_id=<uuid>&scope=all&filter=addressed&start_from=<head|seq>[&expected_generation=<g>]&client=ravel-adapter&client_version=0.1`
  with `Authorization: Bearer <api_key>`.
- First frame `connection_state`: keep `generation` and `cursor`.
- Server sends `{"type":"ping"}` every 2 s. Reply **immediately** with
  `{"type":"pong","cursor":<last seq>}`. No answer for 6 s → evicted `heartbeat_lapsed`.
  **So never run Ravel (slow) on the socket thread.**
- Domain frame: `{"event":"message","data":{"type","room_id","bridge_id","channel_type","payload","sequence"},"id":<seq>}`.
- `message` payload: `addressed`, `sender`, `sender_name`, `message_id`, `body`,
  `timestamp`, `thread_id`, `attachments`. Act only when `addressed` is true. Treat
  `sender` ids as opaque strings.
- `evicted.code`: `taken_over` → stop for good; `heartbeat_lapsed` / `no_stream` /
  `unfenced` / `connection_error` → reconnect from cursor; `closed` → log reason, don't auto-retry.
- Close codes: 4401 bad key (stop), 4409 conflict (stop), 4400 bad params (stop, bug),
  1011/1012/network drop → reconnect with backoff.
- `gap` frame → set cursor = `resumed_at`; carry on.
- Reuse the same `connection_id` on reconnect; pass `expected_generation`.

**Sending:** `POST {BASE}/agents/{id}/message` `{room_id, content}` needs no connection.
Operations: `POST /agents/{id}/ops/{op}` with the args object unwrapped, plus header
`X-Switch-Connection-Id` when the op needs a room. `GET /agents/{id}/ops` lists every
op with its `input_schema`; **read schemas at runtime, don't hard-code**. Useful ops:
`list_rooms`, `post_message`, `send_targeted_message`, `read_context`,
`create_room_document`, `attach_reference_to_room`, `create_room`,
`invite_agent_to_room`, `add_users_to_room`.

**Templates:** spec at `github.com/sandbox-quantum/switch/blob/main/docs/TEMPLATES.md`.
Agent `addressing` in templates is `owner | owner-agents | anyone`. Import:
Console → **Templates** → **Import template**.

**Local server:** Console → "Run a server on this computer" needs Docker running. It
starts a Mattermost alongside it.

## 4. Ravel adapter design (Phases 4–5)

### 4.1 Config (`.env.example`, replace the SWITCH_* lines) `[SONNET]`
```
SWITCH_URL=http://localhost:8000          # bridge base URL; check with /health
SWITCH_REGISTRATION_KEY=                  # Gateway → API Keys → Create Registration Key
RAVEL_AGENT_ID=                           # written by register.py
RAVEL_AGENT_KEY=                          # written by register.py (secret)
SCANNER_AGENT_ID=
SCANNER_AGENT_KEY=
SECURITY_OWNER=                           # the security owner's Switch participant id, for the ledger
RAVEL_REACH_CMD=...  RAVEL_WIKI_CMD=...  RAVEL_CALLERS_CMD=...   # from the owner, Phase 4
DEMO_REPO_PATH=./demo-app
```
Load `.env` with a 10-line stdlib parser in `ravel_adapter/config.py` (no python-dotenv).

### 4.2 Files
| File | Job |
| --- | --- |
| `ravel_adapter/config.py` | Read `.env` + env vars. One place for all settings |
| `ravel_adapter/register.py` | `python -m ravel_adapter.register ravel` (or `sec-scanner`): register once, write id + key into `.env`, set addressing. On 409 print what to do; never pass `overwrite` silently |
| `ravel_adapter/ravel.py` | Ravel side: `run_ravel`, `handle(text)`, output formatting (moved out of adapter.py) |
| `ravel_adapter/switch_client.py` | Protocol side: WebSocket loop, pong, reconnect, `send(room_id, text)`, `call_op(name, args)` |
| `ravel_adapter/adapter.py` | Entry point. `python ravel_adapter/adapter.py "@ravel ..."` = local test; no args = connect to Switch |
| `ravel_adapter/README.md` | Plain-language explainer (Phase 5) |
| `.ravel_state.json` | `connection_id`, `cursor`, `generation`. Add to `.gitignore` |

### 4.3 WebSocket loop (switch_client.py) `[SONNET]`, the precise spec
1. Load/create `connection_id` (uuid4) in `.ravel_state.json`.
2. Open the socket (URL in §3). On a `connection_state` frame, save `generation` and `cursor`.
3. Main thread only reads frames, answers pings at once, and updates the cursor.
4. `message` frame with `payload.addressed` and `payload.sender != own id` → submit
   `(room_id, thread_id, body)` to a `ThreadPoolExecutor(max_workers=2)`. The worker calls
   `ravel.handle(body)` and then `send(...)`. Reply in the same thread if `post_message`'s
   schema accepts a thread id; otherwise post to the room.
5. Advance the cursor (and persist it) after submitting, so one slow command never blocks pings.
6. Reconnect rules from §3. Backoff 1, 2, 4, 8, 16, 30 s, reset after 60 s of healthy connection.
7. Log one line per event: `[ravel] <time> <room> <sender_name>: <first 60 chars>` and
   `[ravel] replied in <n>s`. Never log the API key.
8. Mention stripping: remove a leading `@ravel` or `@<display name>`, case-insensitive,
   before parsing. Log the raw body once in Phase 5 to see the real mention format.

### 4.4 Ravel side (ravel.py) `[SONNET]`, after the owner gives the CLI (Phase 4)
- Commands: `check <file>:<function>`, `verify <branch> <function>`, `wiki <module>`,
  `who calls <function>`, `attach wiki <module>`, `help`.
- **Chat format** (keep under ~12 lines):
  ```
  🔴 REACHABLE · HIGH · app.py:search (B608 SQL injection)
  Path: GET /api/search → search_view() → search()
  ```
  ```
  🟢 UNREACHABLE · legacy_utils.py:eval_expr (B307 eval)
  Proof: 0 callers; not reachable from any route.
  ```
- `verify <branch> <fn>`: `git worktree add --detach .ravel-worktrees/<branch> <branch>`,
  run reach + callers against `.ravel-worktrees/<branch>/demo-app`, then
  `git worktree remove --force`. Add `.ravel-worktrees/` to `.gitignore`. Reply format:
  `✅ FIX VERIFIED on fix/sqli-search · search() no longer reachable with untrusted input` plus
  the callers list. If it's still reachable: `❌ STILL REACHABLE` plus the path.
  ⚠️ `[OPUS]` check: does Ravel's reachability distinguish a *parameterized* query from an
  unsafe one? If it only checks the call graph, `search()` stays reachable after the fix.
  Then verify must also confirm the bandit finding (B608) is gone on the branch:
  `bandit -r <worktree>/demo-app -x tests -f json`. Decide the exact verdict rule in Phase 4.
- Wiki: pre-generate once into `ravel_adapter/wiki_cache/<module>.md` (committed), served
  instantly. `attach wiki <module>` posts it into the room as a **room document**
  (`create_room_document`, schema from `GET /ops`) so it becomes room knowledge.
  Fallback if that op needs a claimed room we can't get: post the wiki as a message and
  note it in PROGRESS.md.
- Timeouts: 120 s per Ravel call. On error, reply `Ravel error: <short reason>` and never
  crash the loop.

### 4.5 Unit tests (`ravel_adapter/tests/`) `[SONNET]`
- `test_handle.py`: command parsing, mention stripping, unknown command → help text.
  Mock `subprocess.run`.
- `test_switch_client.py`: feed fake frames (ping → pong sent first; addressed message →
  job submitted; not-addressed → ignored; `evicted taken_over` → stop; `gap` → cursor
  updated). No network.

## 5. Switch template (Phase 3) `[OPUS]` review, `[SONNET]` edit

Rewrite `switch/security-room.template.yaml` as a **version 1 group template**. This is a
draft; validate it in Console (it shows warnings while typing) and against TEMPLATES.md:

```yaml
version: 1
params:
  repo_dir:
    type: directory
    label: Folder of your ravel-security-room clone
  bridge:
    type: bridge
    default: [Discord, Mattermost, $first]
  provider:
    type: provider
    default: [claude, opencode]
    input: advanced
  location:
    type: location
    default: local
    input: advanced
agents:
  - name: sec-triager
    description: Reads security findings, checks them with ravel, opens fix rooms
    provider: "{provider}"
    location: "{location}"
    directory: "{repo_dir}"
    addressing: anyone            # developers can report issues to it
    instructions: |
      (see §6 for the full text)
  - name: sec-fixer
    description: Patches reachable findings on a branch and runs the tests
    provider: "{provider}"
    location: "{location}"
    directory: "{repo_dir}"
    addressing: owner-agents      # the owner + the owner's agents only; teammates get a visible refusal
    instructions: |
      (see §6)
group:
  name: Security
rooms:
  - name: security-intake
    bridge: "{bridge}"
    agents: [sec-triager, sec-fixer, ravel, sec-scanner]   # ravel + sec-scanner must exist first (C4)
    users: ["{$creator}"]
    kickoff: |
      @sec-triager this is the security intake room. Findings arrive here from sec-scanner.
  - name: security-ledger
    bridge: "{bridge}"
    agents: [sec-triager]
    users: ["{$creator}"]
links:
  - { from: security-intake, to: security-ledger, label: decisions }
```
Open questions for Opus in Phase 3: does a top-level `agents:` list mix with `group:/rooms:`
in v1 (TEMPLATES.md implies yes)? Does the local server have agent management on?

## 6. Agent instructions and the approval gate `[OPUS]`

The gate is three layers. Explain all three in the README ("How Switch is used"):
1. **Switch addressing:** sec-fixer accepts instructions only from the security owner and the owner's agents.
   A teammate typing "approved" gets a **visible refusal from Switch**. Show this in the demo.
2. **Instructions:** sec-fixer merges only when the message is from the human security
   owner (a user participant, not an agent) and says exactly `approved`. Anything else
   → no merge, ask what to change.
3. **Proof before asking:** sec-fixer may ask for approval only after pytest passes and
   ravel says FIX VERIFIED.

Write the final instruction text for both agents in Phase 3. It must cover: the exact
`@ravel` commands to use, the room naming `fix-<short-name>`, that the triager uses its
Switch tools `create_room`, `invite_agent_to_room` and `add_users_to_room`, and asks
`@ravel attach wiki <module>`, the ledger line format
`✅ Fixed | B608 app.py:search | verified by ravel | approved by <owner> | <date>` /
`🟢 Dismissed | B307 legacy_utils.py:eval_expr | unreachable (ravel) | <date>`,
and "never merge or approve yourself".

## 7. Phases (remaining)

### Phase 3 — Switch up and running (Day 1–2)
1. `[OWNER]` Install Docker Desktop (Apple Silicon), open it, wait for "running".
2. `[OWNER]` Download Switch Console (`switch-console-arm64.dmg` from the Switch releases),
   choose **Run a server on this computer**, finish setup, sign in to the bundled
   Mattermost, and link your messaging account.
3. `[SONNET]` Move the demo app to port 8080 (C2): `app.run(port=int(os.environ.get("PORT", 8080)))`,
   then update the README, CLAUDE.md §5 and PROGRESS.md. Re-run Phase 1 checks.
4. `[SONNET]` `curl http://localhost:8000/health` to confirm the bridge base URL. Record it.
5. `[OWNER]` Console: add agent **sec-triager**, provider Claude Code, working directory =
   this repo. Mention it in a Mattermost channel.
6. `[OPUS]` Finish the template (§5) + instructions (§6). Don't import it yet (needs ravel, Phase 5).
- **Done when:** sec-triager replies in Mattermost.

### Phase 4 — Ravel adapter, Ravel side (Day 2)
1. `[OWNER]` Tell us: how judges install Ravel (pip? repo?), and the real commands +
   sample output for reachability, wiki, callers. **Blocker for this phase.**
2. `[SONNET]` Split adapter.py into config.py / ravel.py / adapter.py (§4.2), set
   `RAVEL_*_CMD`, implement formatting (§4.4), wiki cache, worktree-based verify.
3. `[OPUS]` Decide the verify verdict rule (the ⚠️ in §4.4).
4. `[SONNET]` Unit tests §4.5 (`test_handle.py`).
- **Done when:** all of these print correct answers with no Switch:
  `check app.py:search`, `check legacy_utils.py:eval_expr`,
  `check vendor/old_parser.py:parse`, `wiki app`, `who calls process_payment` (→ 2 callers:
  `checkout_view`, `retry_job`).

### Phase 5 — Ravel adapter, protocol side (Day 2)
1. `[SONNET]` Add `websocket-client` to requirements.txt (pin the latest 1.x), then
   `config.py`, `register.py`, `switch_client.py` exactly as §4.3, plus `test_switch_client.py`.
2. `[OWNER]` Gateway (http://localhost:3000) → API Keys → Create Registration Key → paste
   into `.env` as `SWITCH_REGISTRATION_KEY`.
3. `[SONNET]` Run `python -m ravel_adapter.register ravel` and
   `python -m ravel_adapter.register sec-scanner`. Set ravel's addressing to `anyone`.
4. `[OWNER]` Add `ravel` to a Mattermost room (Console → room → add agent).
5. `[SONNET]` Run the adapter, test `@ravel check app.py:search` in chat, and log the raw
   payload once to confirm the field names.
6. `[SONNET]` `ravel_adapter/README.md`.
- **Done when:** `@ravel check app.py:search` in Mattermost gets Ravel's answer, and killing
  and restarting the adapter resumes without duplicate replies.

### Phase 6 — Full workflow (Day 2–3)
1. `[OWNER]` Import the template (§5) in Console → Templates → Import, then Use.
2. `[SONNET]` `scripts/post_findings.py`: run `scan.sh` → read `findings.json` → find the
   `security-intake` room id (`list_rooms` op with the scanner key) → post one message per
   finding from **sec-scanner**: `@sec-triager New finding B608 in demo-app/app.py:34 (search):
   Possible SQL injection…`. Wait about 2 s between posts.
3. `[SONNET]` `scripts/reset_demo.sh`: `git checkout main`, `git reset --hard <DEMO_BASE tag>`
   (create tag `demo-base` on the 3-finding commit), delete local `fix/*` branches,
   `git worktree prune`, remove `demo-app/demo.db`, re-run scan (assert 3). **Ask the owner
   before the first run** (it uses `reset --hard`). Never touch `origin`.
4. `[OPUS]` Run the 8-step flow (CLAUDE.md Phase 6) and tune the instructions where agents
   go off-script. Expect 2–3 rounds.
- **Done when:** 3 clean runs in a row from `reset_demo.sh`.

### Phase 7 — Ask Ravel + Discord (Day 3)
1. `[SONNET]` Check `@ravel who calls process_payment` and `@ravel wiki payments` in any room.
2. `[OWNER]` Connect Discord (Console → server Home → Messaging apps; doc
   `/switch-rooms/deploy/messaging-apps/discord`), create the channels, run the flow there.
3. `[OWNER]` Optional demo moment: a second account plays "developer" and types "approved"
   → Switch refuses.
- Cut order if late: Discord (keep Mattermost) → Ask Ravel. **Never cut** the approval gate or verify.

### Phase 8 — Submission polish (Day 4, freeze 12 PM IST Nov 7)
- `[OPUS]` README pitch + "How Switch is used" + Mermaid architecture; `docs/VIDEO_SCRIPT.md`.
- `[SONNET]` README quickstart (under 15 min, every command copy-pasteable), `docs/BLOG.md`
  draft from PROGRESS.md notes ("one thing that broke": the SSE→WebSocket and port-8000 findings).
- `[SONNET]` Fresh-clone test in the scratchpad: follow the README word for word and fix every gap.
- `[OWNER]` Record the video, submit by 9 PM IST.

## 8. Risks

| Risk | Plan |
| --- | --- |
| Ravel not installable by judges | Ask in Phase 4. Fallback `[OPUS]`: commit wiki cache + document that reach/callers need Ravel |
| Agents improvise in the demo | Strict instructions (§6), `post_findings.py` for the same start each time, 3 dry runs |
| Port clash 8000 | Demo app → 8080 (C2) |
| Duplicate replies after reconnect | Persisted cursor + `expected_generation` (§4.3) |
| Secrets leak | `.env` + `.ravel_state.json` gitignored; check with `git status` before every commit |
| Docker/Console setup eats Day 2 | Start Phase 4 coding (no Switch needed) while Docker installs |
