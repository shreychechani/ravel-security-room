"""All settings for the ravel adapter, in one place.

Values come from environment variables first, then from the repo's `.env` file.
Standard library only (no python-dotenv).
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # the ravel-security-room repo


def load_env_file(path):
    """Read KEY=value lines. Ignores blanks, comments and trailing `# comments`."""
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.split(" #")[0].strip().strip("'\"")
        values[key.strip()] = value
    return values


_FILE = load_env_file(ROOT / ".env")


def get(key, default=""):
    return os.environ.get(key) or _FILE.get(key) or default


def path_setting(key, default):
    """A path from settings; relative paths are relative to the repo root."""
    return (ROOT / get(key, default)).resolve()


# Switch (used by the protocol side)
SWITCH_URL = get("SWITCH_URL", "http://127.0.0.1:8000").rstrip("/")
SWITCH_REGISTRATION_KEY = get("SWITCH_REGISTRATION_KEY")
RAVEL_AGENT_ID = get("RAVEL_AGENT_ID")
RAVEL_AGENT_KEY = get("RAVEL_AGENT_KEY")
SCANNER_AGENT_ID = get("SCANNER_AGENT_ID")
SCANNER_AGENT_KEY = get("SCANNER_AGENT_KEY")
SECURITY_OWNER = get("SECURITY_OWNER")

# Ravel (a separate repo, run with uv)
RAVEL_DIR = path_setting("RAVEL_DIR", "../Ravel")
UV_BIN = get("UV_BIN", "uv")
DEMO_REPO_PATH = path_setting("DEMO_REPO_PATH", "./demo-app")
RAVEL_TIMEOUT = int(get("RAVEL_TIMEOUT", "120"))   # seconds per Ravel run
