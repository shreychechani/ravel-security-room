#!/usr/bin/env bash
# Runs the security scanner on the demo app and writes findings.json.
# Expect 3 findings: SQL injection (B608), eval (B307), unsafe yaml.load (B506).
set -e
cd "$(dirname "$0")/.."
bandit -r demo-app -x demo-app/tests -f json -o findings.json || true
python3 - <<'PY'
import json
for r in json.load(open("findings.json"))["results"]:
    print(f"{r['test_id']}  {r['filename']}:{r['line_number']}  {r['issue_text']}")
PY
