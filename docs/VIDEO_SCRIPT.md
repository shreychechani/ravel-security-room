# Demo video script (3:00)

Target length 3:00 at most. About 430 words of voiceover, so speak at a normal pace.
The agents take a few minutes in real time: **record the whole run once, then cut and speed up**
the waiting (2× to 4×). Never fake a step: every chat message on screen comes from the real run.

## Before you record

- [ ] `./scripts/reset_demo.sh` → "Baseline confirmed: 3 findings on main"
- [ ] Old `fix-*` room deleted in Switch; `#security-intake` and `#security-ledger` scrolled to
      empty (or new channels)
- [ ] ravel running from `../ravel-run` and showing `connected`
- [ ] sec-triager answered the kickoff and named the security owner
- [ ] Chat app (Discord, or Mattermost as fallback) zoomed to about 125%, dark theme, notifications off
- [ ] Two windows ready: chat (main) and a terminal with a large font
- [ ] Optional, for the "Switch refuses" beat: a second chat account logged in in a private window

## Script

### 0:00–0:20 · The problem

**Screen:** terminal, `./scripts/scan.sh` printing the 3 findings. Then a title card:
*"Which of these is real?"*

**Voiceover:**
> AI writes more code than humans can review. Scanners flag everything, so teams stop
> reading the alerts, and the real bug ships with the noise. Here are three findings from
> bandit. Only one of them matters. Which one?

### 0:20–0:40 · The setup

**Screen:** Switch Console showing the agents sec-triager, sec-fixer, ravel and sec-scanner.
Quick cut to the chat sidebar: `#security-intake`, `#security-ledger`.

**Voiceover:**
> This is Ravel Security Room, built on Switch. Switch puts AI agents into our team chat.
> sec-triager and sec-fixer are Claude Code agents. ravel is our own agent: it holds a live
> connection to Switch and answers with proof from the code's call graph. I'm the security
> owner, the only person who can approve a merge.

### 0:40–1:50 · The live run: triage

**Action:** in the terminal, run `python scripts/post_findings.py`. Switch to chat.

**Screen:** `#security-intake`. The 3 findings arrive, sec-triager restates each one and asks
`@ravel check …`. Speed up the waiting.

**Voiceover (0:40–1:05):**
> The findings land in the intake room. sec-triager doesn't guess. For each one, it asks ravel.

**Screen:** zoom in on ravel's two 🟢 UNREACHABLE replies and the "Dismissed …" lines.

**Voiceover (1:05–1:25):**
> The eval and the YAML loader are unreachable. Nothing calls them, and ravel shows the proof:
> zero callers and no route. Two dismissed in seconds, each with a reason anyone can check.

**Screen:** zoom in on ravel's 🔴 REACHABLE reply with
`Path: GET /api/search → search_view() → search()`. Then sec-triager posts
"Opened #fix-sqli-search", and the new room appears in the sidebar.

**Voiceover (1:25–1:50):**
> The SQL injection is real: a public route reaches it in two hops. So sec-triager opens a
> dedicated room for it, brings in sec-fixer, ravel and me, and ravel attaches the module's
> wiki as room knowledge.

### 1:50–2:30 · Fix, verify, approve

**Screen:** `#fix-sqli-search`. The "📄 Attached wiki: app" reply, the brief to sec-fixer, then
sec-fixer's evidence post: the two-line diff, `2 passed`, and ravel's
`✅ FIX VERIFIED on fix/sqli-search`. Speed up the waiting.

**Voiceover (1:50–2:10):**
> sec-fixer branches, switches to a parameterized query, and runs the tests: the injection
> test turns green. Then it asks ravel to verify. Ravel re-scans the branch: the finding is
> gone, and nothing is reachable.

**Optional beat (cut it if over time):** from the second account, type `@sec-fixer approved`.
Show Switch's refusal.

> Someone else tries to approve. Switch refuses before the agent even sees the message.

**Action:** as the security owner, type `@sec-fixer approved`.

**Screen:** sec-fixer's merge message with the commit hash and `2 passed`.

**Voiceover (2:10–2:30):**
> Only one message merges this: "approved", from me. Not "looks good", and not another agent.
> I type it, and sec-fixer merges.

### 2:30–3:00 · Result and why Switch

**Screen:** `#security-ledger` with the three lines (two 🟢 Dismissed, one ✅ Fixed … approved by
@you). Then end card: the headline numbers and the repo URL.

**Voiceover:**
> Every decision is one line in the ledger. Three findings in, two dismissed with proof, one
> fixed and verified, and one human approval. This only works because of Switch: rooms per
> finding, agents that wake when they're addressed, a gate that Switch itself enforces, and
> knowledge attached to the room. Ravel Security Room. Clone it and run it from the README.

**End card text:**
```
3 findings → 2 dismissed with proof → 1 fixed → verified by Ravel → 1 human approval
github.com/shreychechani/ravel-security-room
Built on Switch · Flip the Switch hackathon
```

## Editing notes

- Put captions on the key chat lines (REACHABLE path, FIX VERIFIED, approved). Judges may watch
  muted.
- If the run is over time, cut first: the optional refusal beat, then the setup shot of Console.
  Never cut the verify step or the approval.
- Export at 1080p. Also export a 10 to 15 second GIF of the 🔴/🟢 verdicts plus "approved" →
  merge for `docs/demo.gif` (the README links it).
