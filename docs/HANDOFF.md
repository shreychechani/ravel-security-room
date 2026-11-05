# Handoff — start here (for teammates and their AI agents)

You're joining **Ravel Security Room**, our entry for the *Flip the Switch* hackathon
(Track 1, Best Business Workflow). **Deadline: Nov 7, 2026, 11:59 PM IST. Feature freeze
12 PM IST Nov 7.** Shrey is the owner and security owner.

Read in this order:
1. This file: status, setup, open tasks, rules.
2. [`ARCHITECTURE.md`](./ARCHITECTURE.md): how everything works and why (decisions D1–D7).
3. [`../PLAN.md`](../PLAN.md): detailed specs per task (§4 adapter, §5 template, §6 gate).
4. [`../PROGRESS.md`](../PROGRESS.md): what happened so far, including what broke.

> **AI agents:** read the files above before writing code. Every Switch fact must come from
> the Switch docs (`https://docs.switchagents.ai`, MCP server `https://docs.switchagents.ai/mcp`,
> HTTP transport). Never invent Switch endpoints or fields. When a task's spec doesn't cover
> something, stop and ask your human. Don't guess.

---

## 1. Status (Nov 5)

| Phase | State |
| --- | --- |
| 1 Environment | ✅ Scan = 3 findings, pytest 1 pass / 1 fail (intended) |
| 2 GitHub | ✅ https://github.com/shreychechani/ravel-security-room (MIT) |
| 3 Switch running | ✅ Local server + Mattermost up, `sec-triager` answers in `#security-intake`. Template + agent instructions **not written yet** (T6) |
| 4 Ravel side of adapter | 🟡 Ravel verified against demo-app (ARCHITECTURE §6). Code not written (T1, T2) |
| 5 Switch protocol side | ⬜ (T3) |
| 6 Full workflow | ⬜ (T4, T5, T6, then dry runs) |
| 7 Ask Ravel + Discord | ⬜ |
| 8 README, blog, video | ⬜ (T8) |

## 2. Setup (15 min, no Switch needed)

```bash
# Clone both repos side by side
git clone https://github.com/shreychechani/ravel-security-room.git
git clone https://github.com/shreychechani/Ravel.git
cd Ravel && uv sync && cd ..            # needs uv (https://docs.astral.sh/uv/), Python 3.12+

cd ravel-security-room
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                    # RAVEL_DIR=../Ravel already matches this layout

./scripts/scan.sh                       # expect 3 findings: B608, B307, B506
pytest demo-app/tests -q                # expect 1 failed, 1 passed (intended until the live fix)
uv run --project ../Ravel ravel scan demo-app --limit 0 --json /tmp/scan.json
                                        # expect B608 reachable; B307, B506 unreachable
```

**Only for live testing in chat (T3 live test, T5, T6, Phase 6):** install Docker Desktop and
Switch Console, then choose *Run a server on this computer*. A local server is single-user,
so each tester runs their own. See ARCHITECTURE §8 for ports.

## 3. Open tasks

Claim a task by telling Shrey and putting your name in the **Who** column (in your PR).
"Switch?" says whether you need a running Switch server.

| ID | Task | Spec | Switch? | Who | Done when |
| --- | --- | --- | --- | --- | --- |
| **T1** | Ravel side of the adapter: `ravel_adapter/config.py` (stdlib `.env` reader), `ravel_adapter/ravel.py` with `check`, `who calls`, `verify`, `wiki`, `help`; chat formatting; ignore `tests/` findings; read `@app.route` for the URL | PLAN §4.2, §4.4; ARCHITECTURE §6, D2, D3, D6 | No | | `python ravel_adapter/adapter.py "@ravel check app.py:search"` (and the other 4 commands in PLAN §7 Phase 4) print correct answers |
| **T1b** | Wiki generator: build `ravel_adapter/wiki_cache/<module>.md` from `scan.json` (functions, routes, callers, callees, findings) and commit the pages | ARCHITECTURE D3 | No | | `wiki app`, `wiki payments` print useful pages instantly |
| **T2** | `ravel_adapter/tests/test_handle.py`: parsing, mention stripping, unknown → help; mock `subprocess.run` | PLAN §4.5 | No | | `pytest ravel_adapter/tests -q` green |
| **T3** | Protocol side: `register.py`, `switch_client.py` (WebSocket loop, pong, reconnect, cursor), `tests/test_switch_client.py` with fake frames | PLAN §3, §4.3, §4.5 | Unit tests: no. Live test: yes | | Fake-frame tests green; then `@ravel check app.py:search` answered in Mattermost |
| **T4** | `scripts/reset_demo.sh` + tag `demo-base` | PLAN §7 Phase 6.3 | No | | Running it twice leaves `main` with 3 findings, no `fix/*` branches. **Ask Shrey before the first run (`reset --hard`)** |
| **T5** | `scripts/post_findings.py`: post the 3 findings as sec-scanner into `#security-intake` | PLAN §7 Phase 6.2 | Yes | | 3 messages appear, ~2 s apart |
| **T6** | Switch template + final instructions for sec-triager and sec-fixer (approval gate) | PLAN §5, §6; ARCHITECTURE §5; Q1–Q3 below | Writing: no. Import test: yes | Opus session | Template imports in Console without errors |
| **T7** | Connect Discord, run the flow there | PLAN §7 Phase 7 | Yes | Shrey | Flow works in Discord |
| **T8** | Drafts: `docs/BLOG.md`, `docs/VIDEO_SCRIPT.md`, README "How Switch is used" | CLAUDE.md Phase 8 | No | | Drafts reviewed by Shrey |
| **T9** | Add an MIT `LICENSE` file to the Ravel repo (pyproject says MIT, the file is missing) | — | No | Shrey | File on GitHub |

Dependencies: T1 → T2 and T1b. T1 + T3 → live `@ravel`. T3 (register) → T5 and T6 import.
T1–T6 → Phase 6 dry runs (3 clean runs in a row from `reset_demo.sh`).

**Can run in parallel right now with no Switch:** T1, T1b, T2, T3 (unit part), T4, T8.

## 4. Open questions (decide in T6)

- **Q1. sec-fixer's working directory.** Console agents default to an empty folder
  (`~/.switch/agents/...`). sec-fixer needs a real git checkout. If it's this repo, Claude Code
  also loads `CLAUDE.md`, the *builder's* rulebook. `CLAUDE.md` now starts with a note telling
  room agents to ignore it, so pointing Directory at the repo is likely fine. Confirm in a dry run.
- **Q2. Addressing for sec-fixer:** default "Me and my agents" vs "Custom rules" (name the owner
  plus sec-triager only). Does the template YAML support custom rules?
- **Q3. Auto mode / Bypass permissions for sec-fixer.** It runs git and pytest. Bypass would
  weaken the gate story; Auto mode may still prompt mid-demo.
- **Q4. Do Console's random ports survive a server restart / reboot?** If not, `SWITCH_URL`
  in `.env` must be updated after restarts (or `config.py` reads `ports.json`).

## 5. Rules (everyone, humans and agents)

- **Never fix finding 1 (SQL injection) on `main`.** The fix happens live, by sec-fixer, in the demo.
  `main` must always scan to exactly 3 findings (B608, B307, B506).
- **Never commit `.env`**, agent keys, or `.ravel_state.json`. Check `git status` before each commit.
- Work on a branch (`task/T1-ravel-side`), open a PR to `main`; Shrey merges.
- Python 3.11+, stdlib + `requirements.txt` only. Ravel's deps stay in the Ravel repo (D4).
  New dependencies need Shrey's OK.
- Keep code small and readable; judges must understand it quickly.
- After finishing a task, add a short entry to `PROGRESS.md` (done / broken / next).
- Ask Shrey before: pushing to `main`, creating repos, installing global tools, deleting
  files, anything that costs money.
