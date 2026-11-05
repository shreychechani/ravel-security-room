# Ravel Security Room

AI writes more code than humans can review. Ravel Security Room lets agents sort real
vulnerabilities from noise, fix them, prove the fix works, and wait for a human
"approved" in Discord, Slack or Mattermost. Built on [Switch](https://github.com/sandbox-quantum/switch)
for the Flip the Switch hackathon.

> Work in progress. Full README (setup, demo video, architecture) comes on Day 4.
>
> **Teammates and their agents: start at [`docs/HANDOFF.md`](docs/HANDOFF.md)** (status, setup,
> open tasks), then [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (how it works and why).

## Repo layout

| Path | What it is |
| --- | --- |
| `demo-app/` | Small Flask app with 3 planted findings (1 reachable, 2 not) |
| `switch/security-room.template.yaml` | Switch agent template: sec-triager + sec-fixer + intake room |
| `ravel_adapter/` | Connects Ravel to Switch as its own agent |
| `scripts/scan.sh` | Runs bandit and lists the 3 findings |

## Quick local check

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/scan.sh                 # expect 3 findings
pytest demo-app/tests -q          # expect 1 failing test until the SQL injection is fixed
cd demo-app && python app.py      # http://127.0.0.1:8080/api/search?q=almo
```
