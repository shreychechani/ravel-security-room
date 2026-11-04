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
- App on port 8000: `GET /api/search?q=almo` → `[[1,"almonds"]]`

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
