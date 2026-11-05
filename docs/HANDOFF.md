# Handoff — start here (for teammates and their AI agents)

You're joining **Ravel Security Room**, our entry for the *Flip the Switch* hackathon
(Track 1, Best Business Workflow). **Deadline: Nov 7, 2026, 11:59 PM IST. Feature freeze
12 PM IST Nov 7.** The project owner is also the **security owner**, the only person who approves merges.

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
| 3 Switch running | ✅ Local server + Mattermost up, `sec-triager` answers in `#security-intake`. Template + agent instructions written (T6); import test is next |
| 4 Ravel side of adapter | ✅ T1 + T1b done: all commands answer correctly with no Switch. Tests (T2) open |
| 5 Switch protocol side | ✅ T3 done: `ravel` and `sec-scanner` registered; `check`, `who calls`, `attach wiki` answered live in Mattermost (~1.5 s). See `ravel_adapter/README.md` |
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

**Only for live testing in chat (T5, T6, Phase 6):** install Docker Desktop and
Switch Console, then choose *Run a server on this computer*. A local server is single-user,
so each tester runs their own. See ARCHITECTURE §8 for ports. To run Ravel in chat
(registration key, registering agents, starting it), follow `ravel_adapter/README.md` → *Run it*.
Console 0.40.1 has no Gateway page, so the key comes from `python -m ravel_adapter.registration_key`.

## 3. Open tasks

Claim a task by telling the project owner and putting your name in the **Who** column (in your PR).
"Switch?" says whether you need a running Switch server.

| ID | Task | Spec | Switch? | Who | Done when |
| --- | --- | --- | --- | --- | --- |
| **T1** ✅ | Ravel side of the adapter: `ravel_adapter/config.py` (stdlib `.env` reader), `ravel_adapter/ravel.py` with `check`, `who calls`, `verify`, `wiki`, `help`; chat formatting per the **reply contract** (replies start with `@<asker>`); ignore `tests/` findings; read `@app.route` for the URL | PLAN §4.2, §4.4; ARCHITECTURE §6 (reply contract), D2, D3, D6 | No | | `python ravel_adapter/adapter.py "@ravel check app.py:search"` (and the other 4 commands in PLAN §7 Phase 4) print correct answers |
| **T1b** ✅ | Wiki generator: build `ravel_adapter/wiki_cache/<module>.md` from `scan.json` (functions, routes, callers, callees, findings) and commit the pages | ARCHITECTURE D3 | No | | `wiki app`, `wiki payments` print useful pages instantly |
| **T2** | `ravel_adapter/tests/test_handle.py`: parsing, mention stripping, unknown → help; mock `subprocess.run` | PLAN §4.5 | No | | `pytest ravel_adapter/tests -q` green |
| **T3** ✅ | Protocol side: `register.py`, `switch_client.py` (WebSocket loop, pong, reconnect, cursor), `tests/test_switch_client.py` with fake frames | PLAN §3, §4.3, §4.5 | Unit tests: no. Live test: yes | | Fake-frame tests green; then `@ravel check app.py:search` answered in Mattermost |
| **T4** | `scripts/reset_demo.sh` + tag `demo-base` | PLAN §7 Phase 6.3 | No | | Running it twice leaves `main` with 3 findings, no `fix/*` branches. **Ask the owner before the first run (`reset --hard`)** |
| **T5** | `scripts/post_findings.py`: post the 3 findings as sec-scanner into `#security-intake` | PLAN §7 Phase 6.2 | Yes | | 3 messages appear, ~2 s apart |
| **T6** | ✅ Written: `switch/security-room.template.yaml` (both agents' instructions, approval gate, 2 rooms). **Left:** import test | ARCHITECTURE §5, D8–D12; §4 below | Import: yes | Owner | Template imports and runs without errors (after T3 registers ravel + sec-scanner) |
| **T7** | Connect Discord, run the flow there | PLAN §7 Phase 7 | Yes | Owner | Flow works in Discord |
| **T8** | Drafts: `docs/BLOG.md`, `docs/VIDEO_SCRIPT.md`, README "How Switch is used" | CLAUDE.md Phase 8 | No | | Drafts reviewed by the owner |
| **T9** | Add an MIT `LICENSE` file to the Ravel repo (pyproject says MIT, the file is missing) | — | No | Owner | File on GitHub |

Dependencies: T1 → T2 and T1b. T1 + T3 → live `@ravel`. T3 (register) → T5 and T6 import.
T1–T6 → Phase 6 dry runs (3 clean runs in a row from `reset_demo.sh`).

**Can run in parallel right now with no Switch:** T2, T4, T8.

## 4. Import the template (`ravel` and `sec-scanner` must be registered, and `adapter.py` running)

1. **Remove the Phase 3 test setup** so names don't clash: in Switch Console, delete the
   hand-made `sec-triager` agent (Your Agents → sec-triager) and the test room
   `security-intake` (archive its channel when asked).
2. Console → **Templates** → **Import template** → paste `switch/security-room.template.yaml`.
   Fix any warning it shows, then **Use**.
3. Fill in: **Security owner** = your chat username; **Folder** = full path of your
   ravel-security-room clone. Leave the rest. Select **Create all**.
4. Expect: `#security-intake` (with sec-triager, ravel, sec-scanner, you, a
   `triage-playbook` room document) and `#security-ledger`. sec-triager answers the kickoff.

## 5. Open questions

Decided in T6 (see ARCHITECTURE D8–D12): sec-fixer works in the repo clone and sec-triager
in its own empty folder; sec-fixer addressing `owner-agents` (custom rules can't be written in
a template); Auto mode on, Bypass off.

- **Q4. Do Console's random ports survive a server restart / reboot?** If not, `SWITCH_URL`
  in `.env` must be updated after restarts (or `config.py` reads `ports.json`).
- **Q5. Watch in the dry runs:** does Auto mode stop sec-fixer with permission prompts for
  `git`/`pytest`? (If yes: a narrow allowlist, never Bypass.) Can sec-triager invite agents and
  add users to a room it created? Does sec-triager reliably wait for ravel's reply?

## 6. Rules (everyone, humans and agents)

- **Never fix finding 1 (SQL injection) on `main`.** The fix happens live, by sec-fixer, in the demo.
  `main` must always scan to exactly 3 findings (B608, B307, B506).
- **Never commit `.env`**, agent keys, or `.ravel_state.json`. Check `git status` before each commit.
- Work on a branch (`task/T1-ravel-side`), open a PR to `main`; the owner merges.
- Python 3.11+, stdlib + `requirements.txt` only. Ravel's deps stay in the Ravel repo (D4).
  New dependencies need the owner's OK.
- Keep code small and readable; judges must understand it quickly.
- After finishing a task, add a short entry to `PROGRESS.md` (done / broken / next).
- Ask the owner before: pushing to `main`, creating repos, installing global tools, deleting
  files, anything that costs money.
