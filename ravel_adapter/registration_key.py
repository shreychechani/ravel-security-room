"""Create a Switch registration key and save it in .env as SWITCH_REGISTRATION_KEY.

    python -m ravel_adapter.registration_key

Use this when Switch Console has no button for the Gateway's web page (Console 0.40.1 with
a server on this Mac). It calls the Gateway API (POST /gateway/auth/login, then
POST /gateway/api-keys). The email and password come from GATEWAY_ADMIN_EMAIL /
GATEWAY_ADMIN_PASSWORD if set, otherwise it asks (password hidden). The password is never
printed or saved, and the key goes straight into .env (never committed).
"""
import getpass
import os
import sys

import requests

from . import config
from .register import save_to_env


def main():
    if config.SWITCH_REGISTRATION_KEY:
        sys.exit("SWITCH_REGISTRATION_KEY is already set in .env. Nothing to do.")
    gateway = f"{config.SWITCH_URL.rstrip('/')}/gateway"
    email = (os.environ.get("GATEWAY_ADMIN_EMAIL")
             or input("Gateway email [admin@switch.local]: ").strip() or "admin@switch.local")
    password = os.environ.get("GATEWAY_ADMIN_PASSWORD") or getpass.getpass("Gateway password (hidden): ")

    session = requests.Session()   # login sets a session cookie
    resp = session.post(f"{gateway}/auth/login", json={"email": email, "password": password},
                        timeout=30)
    if not resp.ok:
        sys.exit(f"Login failed: HTTP {resp.status_code}. Check the email and password.")

    resp = session.post(f"{gateway}/api-keys", json={"label": "ravel-security-room"}, timeout=30)
    if not resp.ok:
        sys.exit(f"Could not create the key: HTTP {resp.status_code} {resp.text[:200]}")
    save_to_env({"SWITCH_REGISTRATION_KEY": resp.json()["key"]})
    print("Registration key created and saved to .env.")


if __name__ == "__main__":
    main()
