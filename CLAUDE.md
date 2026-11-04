# CLAUDE.md — Ravel Security Room (Flip the Switch hackathon)

Read this whole file before doing anything, then read `PLAN.md`. This file says what we
are building and the rules; `PLAN.md` has the task-by-task plan, verified Switch facts, and
corrections to this file (where they disagree, `PLAN.md` wins). Work phase by phase. At the end of
each phase, stop, report results, and wait for Shrey to say "continue".

---

## 1. Context

- **Event:** "Flip the Switch" hackathon by WeMakeDevs x DevTools Academy, powered by Switch.
- **Deadline:** Nov 7, 2026, 11:59 PM IST. Our own target: submit by **9 PM IST, Nov 7**.
- **Track:** Track 1, Best Business Workflow.
- **Owner:** Shrey (human). You are Claude Code, the main builder.
- **Switch:** open-source infrastructure (github.com/sandbox-quantum/switch) that puts AI
  agents into team chat. Each chat channel (Slack, Discord, Telegram, Mattermost) becomes a
  "room". Agents connect through the **Switch Agent Protocol** (WebSocket in, HTTP out; SSE is deprecated).
  **Switch Console** is the desktop app that runs agents and a local server in Docker.
- **Switch docs:** available to you through the `switch-docs` MCP server
  (`https://docs.switchagents.ai/mcp`, HTTP transport). ALWAYS use it for any Switch fact: template fields,
  protocol endpoints, event formats, auth. Never guess Switch APIs.
- **Ravel:** Shrey's own codebase intelligence tool for Python repos. It builds a call/import
  graph, generates a wiki, and does reachability analysis (can outside input reach a line?).

## 2. What we are building

**Ravel Security Room:** a Switch workflow where AI agents triage security findings,
prove which are real, fix the real one, prove the fix works, and wait for a human
"approved" before merging. All of it happens in team chat.

One-line pitch: *AI writes more code than humans can review. Agents sort real
vulnerabilities from noise, fix them, prove the fix, and a human approves in chat.*

Headline demo result: **3 findings in → 2 dismissed with call-graph proof → 1 fixed and
verified by Ravel → 1 human approval.**

### Judging criteria (optimize for all four)
1. **Use of Switch:** project must not work without Switch. Use rooms, roles, agent
   addressing, multiple agents, attached knowledge, human approval gate.
2. **Technical execution:** a judge can `git clone`, follow the README, and reproduce it.
3. **Creativity and impact:** real team problem (security alert overload, AI-written code).
4. **Presentation:** clear README + 3-minute demo video.

## 3. Architecture

```
Team chat (Mattermost for dev, Discord for the demo)
        │  Collaboration Bridge
Switch Core: rooms, roles, tasks, approval gate
  ├─ #security-intake   every finding / PR lands here
  ├─ #fix-<name>        one room per real finding (fixer + ravel + security owner)
  └─ #security-ledger   one line per decision
        │  Agent Bridge (WebSocket in, HTTP out)
Agents
  ├─ sec-triager  (Claude Code or OpenCode via Switch Console)
  ├─ ravel        (custom agent: ravel_adapter/ + Shrey's Ravel CLI)
  └─ sec-fixer    (Claude Code via Switch Console)
        │
demo-app/  (Flask app with 3 planted findings)
```

### Agents and their jobs
| Agent | Runs via | Job |
| --- | --- | --- |
| sec-triager | Switch Console template | Restate finding, ask ravel, dismiss or open fix room, write ledger line |
| ravel | `ravel_adapter/adapter.py` over the Agent Protocol | `check`, `verify`, `wiki`, `who calls` |
| sec-fixer | Switch Console template | Branch, patch, run tests, ask ravel to verify, merge only after "approved" |

### Ravel's three jobs + bonus
1. **Prove it's real:** reachability verdict + call path for each finding.
2. **Give context:** attach the wiki page of the affected module to each new fix room.
3. **Prove the fix:** re-run reachability on the fix branch; list callers of the changed function.
4. **Bonus, Ask Ravel:** answer `@ravel who calls X` and `@ravel wiki <module>` for any developer.

### Humans (Switch roles)
- **Security owner (Shrey):** the ONLY one who can approve a merge.
- **Developer:** reports issues, asks Ravel questions.

## 4. Repo layout (already exists)

| Path | Purpose |
| --- | --- |
| `demo-app/app.py` | Flask app. FINDING 1: SQL injection in `search()`, reachable from `/api/search` |
| `demo-app/legacy_utils.py` | FINDING 2: `eval()` in `eval_expr()`, never called |
| `demo-app/vendor/old_parser.py` | FINDING 3: unsafe `yaml.load`, module never imported |
| `demo-app/payments.py`, `jobs.py` | For "Ask Ravel": `process_payment` has 2 callers |
| `demo-app/tests/test_app.py` | `test_search_blocks_sql_injection` FAILS until finding 1 is fixed (intended) |
| `scripts/scan.sh` | bandit scan; must print exactly 3 findings: B608, B307, B506 |
| `switch/security-room.template.yaml` | Switch template for sec-triager + sec-fixer + intake room |
| `ravel_adapter/adapter.py` | Ravel side done; Switch protocol side has TODOs |
| `.env.example` | Config; copy to `.env` (never commit `.env`) |

**Do not fix finding 1 on `main` yourself.** The fix must happen live through the
sec-fixer agent in the demo. Keep exactly 3 scanner findings on `main`.

## 5. Rules for you (Claude Code)

- Use `switch-docs` MCP for every Switch detail. If the docs don't answer it, say so and
  ask Shrey; do not invent endpoints, fields or flags.
- Ask Shrey before: pushing to GitHub, creating repos, installing global tools, deleting
  files, or anything that costs money.
- Never commit secrets. `.env` stays in `.gitignore`. Use `.env.example` for placeholders.
- Small commits with clear messages, at least one per working session.
- Python 3.11+, standard library + `requirements.txt` only, unless Shrey approves more.
- macOS: never use port 5000 (AirPlay uses it). Switch's local API uses 8000 and its Gateway 3000, so the demo app runs on **8080**.
- Keep code simple and readable; judges must understand it quickly.
- After each phase, update `PROGRESS.md` (create it) with: done, broken, next.

## 6. Things ONLY Shrey can do (ask him, don't attempt)

- Install and click through **Switch Console** (desktop GUI) and start the local server.
- Connect Discord/Slack to Switch, create channels, set roles in the UI.
- Make Ravel available to judges (public repo or pip package) and tell you its CLI commands.
- Sign the Switch contributor agreement (Track 3), register, record the video, submit.

When you reach one of these, print exact click-by-click instructions for Shrey, then wait.

## 7. Phases (do in order; stop after each)

### Phase 1 — Environment check (Day 1)
- Check: `git`, `python3 --version` (3.11+), `docker --version`, `gh auth status`.
- Create `.venv`, install `requirements.txt`.
- Run `./scripts/scan.sh` → exactly 3 findings. Run `pytest demo-app/tests -q` → 1 pass, 1 fail.
- Run the app on port 8080 and curl `/api/search?q=almo`.
- **Done when:** all of the above pass. Report output.

### Phase 2 — GitHub (Day 1)
- Ask Shrey for approval, then: `git init` (if needed), first commit,
  `gh repo create ravel-security-room --public --source=. --push`.
- Add an MIT `LICENSE`.
- **Done when:** repo is public and pushed. Report the URL.

### Phase 3 — Switch up and running (Day 1, mostly Shrey)
- Give Shrey Console steps: start local server (Mattermost included), add agent
  `sec-triager` with working directory = this repo, provider = Claude Code or OpenCode.
- Using switch-docs, verify every field in `switch/security-room.template.yaml`
  (agents, addressing, provider, instructions, room, bridge, kickoff). Fix it to match
  the current schema. Explain each change.
- **Done when:** Shrey confirms sec-triager replies in a Mattermost channel.

### Phase 4 — Ravel adapter, Ravel side (Day 2)
- Ask Shrey for Ravel's real CLI commands (reachability, wiki, callers) and output format.
- Update `.env` / `.env.example` `RAVEL_*_CMD` lines.
- Make Ravel output short and chat-friendly: verdict (REACHABLE / UNREACHABLE),
  severity, call path like `/api/search → search_view() → search()`.
- Test locally: `python ravel_adapter/adapter.py "@ravel check app.py:search"` and the same
  for the other 2 findings, `wiki app`, `who calls process_payment`.
- Pre-generate Ravel's wiki for `demo-app/` and store it where the adapter can read it fast.
- **Done when:** all 5 commands return correct answers without Switch.

### Phase 5 — Ravel adapter, protocol side (Day 2)
- Read the Agent Protocol docs via switch-docs: how a custom agent registers, authenticates,
  receives events (WebSocket), and sends messages (HTTP), plus how to attach knowledge to a room.
- Replace every `TODO` in `ravel_adapter/adapter.py` with the real protocol. Add reconnect
  on a dropped WebSocket and clear logs.
- Add `ravel_adapter/README.md` explaining how it works in plain language.
- **Done when:** in Mattermost, `@ravel check app.py:search` gets Ravel's answer.

### Phase 6 — Full workflow (Day 2–3)
- Import the template (Shrey) so sec-triager, sec-fixer and `#security-intake` exist.
- Add a script `scripts/post_findings.py` that posts the 3 bandit findings into
  `#security-intake` (via the protocol or Switch API per docs) so the demo starts the same way every time.
- Flow to make work end to end:
  1. Findings posted → sec-triager restates → asks ravel.
  2. ravel: 2 UNREACHABLE (dismissed with proof), 1 REACHABLE.
  3. sec-triager opens `#fix-sqli-search`, adds sec-fixer, ravel, Shrey.
  4. ravel attaches the wiki page for the module as room knowledge.
  5. sec-fixer: branch `fix/sqli-search`, parameterized query, `pytest` passes, asks ravel to verify.
  6. ravel `verify fix/sqli-search search` → no longer reachable + callers list.
  7. Shrey types "approved" → sec-fixer merges. Anything else → no merge.
  8. sec-triager writes the ledger line in `#security-ledger`.
- Set roles/permissions so only Shrey can approve (per docs).
- Add `scripts/reset_demo.sh`: resets `main` to the 3-finding state and deletes fix branches,
  so the demo can be re-run from scratch.
- **Done when:** the full flow runs 3 times in a row from `reset_demo.sh` without manual fixes.

### Phase 7 — Ask Ravel + Discord (Day 3)
- Confirm `who calls` and `wiki` work in any room.
- Shrey connects Discord; run the whole flow there.
- **Cut first if late:** stretch goals, then Ask Ravel. Never cut the approval gate or verify step.

### Phase 8 — Submission polish (Day 4, feature freeze 12 PM IST)
- Rewrite `README.md`: pitch, GIF placeholder, "How Switch is used" section (rooms, roles,
  agents, approval gate, attached knowledge), architecture diagram (Mermaid), quickstart a
  judge can follow in under 15 minutes, demo walkthrough, limits and next steps.
- Write `docs/BLOG.md` draft: what we built, setup steps with exact commands, one thing that
  broke and how we fixed it (use `PROGRESS.md` notes).
- Write `docs/VIDEO_SCRIPT.md` (3 min): problem (0:00–0:20), setup (0:20–0:40), live run
  (0:40–1:50), fix + verify + approve (1:50–2:30), result + why Switch (2:30–3:00).
- Final check: fresh clone into a temp folder, follow README exactly, confirm it works.

## 8. Definition of done (whole project)
- [ ] Public repo, clean README, MIT license, no secrets
- [ ] 3 findings → 2 dismissed with proof → 1 fixed → verified by Ravel → approved by human
- [ ] Wiki context attached in the fix room; Ask Ravel answers questions
- [ ] Works in Discord (or Mattermost as fallback)
- [ ] `reset_demo.sh` makes the demo repeatable
- [ ] README, blog draft, video script ready by Nov 7, 5 PM IST
