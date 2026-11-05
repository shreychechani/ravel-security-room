"""Ravel agent for Switch: entry point.

    python ravel_adapter/adapter.py "@ravel check app.py:search"   # local test, no Switch
    python ravel_adapter/adapter.py                                # connect to Switch (T3)

The Ravel side (commands, formatting) lives in ravel.py.
The Switch side (WebSocket in, HTTP out) will live in switch_client.py (task T3).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ravel  # noqa: E402


def local_test(text):
    reply = ravel.handle(text, sender="you")
    print(reply.text)
    if reply.document:
        name, content = reply.document
        print(f"\n--- room document '{name}' ---\n{content}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        local_test(" ".join(sys.argv[1:]))
    else:
        sys.exit("Switch connection not built yet (task T3). "
                 'For a local test: python ravel_adapter/adapter.py "@ravel help"')
