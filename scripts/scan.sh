#!/usr/bin/env bash
# Runs the security scanner on the demo app and writes findings.json.
# Expect 3 findings: SQL injection (B608), eval (B307), unsafe yaml.load (B506).
set -e
cd "$(dirname "$0")/.."

# Use the project's virtualenv if it exists, so this works without `source .venv/bin/activate`.
if [ -x .venv/bin/bandit ]; then BANDIT=.venv/bin/bandit; else BANDIT=bandit; fi
command -v "$BANDIT" >/dev/null || { echo "bandit not found: run pip install -r requirements.txt" >&2; exit 2; }

# Remove old results so a failed run can never print stale findings.
rm -f findings.json
# bandit exits 1 when it finds issues; that is expected. Any other code is a real error.
"$BANDIT" -r demo-app -x demo-app/tests -f json -o findings.json -q || [ $? -eq 1 ]

python3 - <<'PY'
import json
for r in json.load(open("findings.json"))["results"]:
    print(f"{r['test_id']}  {r['filename']}:{r['line_number']}  {r['issue_text']}")
PY
