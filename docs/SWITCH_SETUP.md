# Switch Setup & Deployment Guide

This guide explains how to set up **Switch Console**, register the custom agents (`ravel` and `sec-scanner`), import the security room template, and run the complete human-in-the-loop workflow.

---

## 1. Prerequisites

- **Switch Console** (macOS or Windows / Linux desktop app): [Download Switch Console](https://github.com/sandbox-quantum/switch).
- **Docker Desktop**: Running locally (used by Switch Console to host the bundled Mattermost instance).
- **Python 3.11+** with dependencies installed:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate    # On Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  ```

---

## 2. Start Switch Local Server

1. Open **Switch Console**.
2. Select **Run a server on this computer**.
3. Console will launch:
   - `switch-core` (native server process)
   - Mattermost (in Docker)
   - PostgreSQL (native or Docker)
4. Verify server health:
   - On macOS: ports are in `~/Library/Application Support/switchdash/local-switch-server/ports.json`.
   - On Windows: `%APPDATA%\switchdash\local-switch-server\ports.json`.
   - Test connectivity:
     ```bash
     python -c "from ravel_adapter import config; print('Switch API:', config.SWITCH_URL)"
     ```

---

## 3. Register Custom Agents

> [!IMPORTANT]
> A Switch room template stops with an error if an agent it references does not exist yet. You must register `ravel` and `sec-scanner` **before** importing the template.

1. **Obtain Registration Key**:
   - In Switch Console 0.40+, run the registration helper:
     ```bash
     python -m ravel_adapter.registration_key
     ```
   - Alternatively, copy the registration key from Gateway $\to$ **API Keys** $\to$ **Create Registration Key** into your `.env` as `SWITCH_REGISTRATION_KEY`.

2. **Register the `ravel` Agent**:
   ```bash
   python -m ravel_adapter.register ravel
   ```
   *(This registers the custom Ravel reachability agent, sets addressing to `anyone`, and stores its credentials in `.env`).*

3. **Register the `sec-scanner` Agent**:
   ```bash
   python -m ravel_adapter.register sec-scanner
   ```
   *(This registers the scanner identity used by `scripts/post_findings.py` to stream Bandit findings into the intake room).*

---

## 4. Import the Security Room Template

1. Validate the template locally:
   ```bash
   python scripts/validate_template.py
   ```
2. In Switch Console:
   - Navigate to **Templates** $\to$ **Import template**.
   - Paste the contents of [`switch/security-room.template.yaml`](../switch/security-room.template.yaml).
   - Click **Use Template**.
3. Fill in the parameters:
   - **Security owner**: Your chat username (e.g. `admin` or your personal username, without `@`).
   - **Folder**: The full path to your `ravel-security-room` repository clone.
   - **Bridge**: Select `Mattermost` (or `Discord`).
4. Click **Create all**.
5. Switch creates:
   - `#security-intake` (with `sec-triager`, `ravel`, `sec-scanner`, you, and the `triage-playbook` document).
   - `#security-ledger` (audit log room with `sec-triager` and you).
   - Auto-wakes `sec-triager` with the intake kickoff prompt.

---

## 5. Start the Ravel Adapter

In a dedicated terminal, launch the Ravel agent adapter:
```bash
python ravel_adapter/adapter.py
```
Expected output:
```text
[ravel] connected to ws://... cursor=...
[ravel] listening for addressed events...
```

---

## 6. Run the Live Triage & Fix Workflow

1. **Post Findings**:
   Stream the 3 scanner findings into the intake channel:
   ```bash
   python scripts/post_findings.py
   ```
2. **Triager Action**:
   - `sec-triager` receives each finding and asks `@ravel check <file>:<function>`.
   - `ravel` answers:
     - `B307` (`legacy_utils.py:eval_expr`) $\to$ **🟢 UNREACHABLE** $\to$ Triager dismisses it with proof.
     - `B506` (`vendor/old_parser.py:parse`) $\to$ **🟢 UNREACHABLE** $\to$ Triager dismisses it with proof.
     - `B608` (`app.py:search`) $\to$ **🔴 REACHABLE** $\to$ Triager dynamically opens room `#fix-sqli-search`.
3. **Fix & Verification in `#fix-sqli-search`**:
   - `ravel` attaches module knowledge: `@ravel attach wiki app`.
   - `sec-fixer` checks out branch `fix/sqli-search`, patches `app.py` with parameterized SQL query, runs tests.
   - `sec-fixer` verifies: `@ravel verify fix/sqli-search search`.
   - `ravel` replies: `✅ FIX VERIFIED on fix/sqli-search · B608 gone from search(); 0 reachable findings`.
4. **Human Approval Gate**:
   - `sec-fixer` posts the diff and requests human approval.
   - An unauthorized user typing `@sec-fixer approved` receives an immediate refusal from Switch.
   - The security owner types `@sec-fixer approved`.
   - `sec-fixer` merges to `main` and posts the commit hash.
5. **Ledger Audit**:
   - `sec-triager` writes the verified audit trail line into `#security-ledger`.
