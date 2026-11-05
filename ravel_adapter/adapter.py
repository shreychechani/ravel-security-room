"""Ravel agent for Switch: entry point.

    python ravel_adapter/adapter.py "@ravel check app.py:search"   # local test, no Switch
    python ravel_adapter/adapter.py                                # connect to Switch and serve

The Ravel side (commands, formatting) lives in ravel.py.
The Switch side (WebSocket in, HTTP out) lives in switch_client.py.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import ravel  # noqa: E402
from switch_client import SwitchClient  # noqa: E402


def local_test(text):
    reply = ravel.handle(text, sender="you")
    print(reply.text)
    if reply.document:
        name, content = reply.document
        print(f"\n--- room document '{name}' ---\n{content}")


def serve():
    logging.basicConfig(format="[ravel] %(asctime)s %(message)s", datefmt="%H:%M:%S",
                        level=logging.INFO)
    if not (config.RAVEL_AGENT_ID and config.RAVEL_AGENT_KEY):
        sys.exit("RAVEL_AGENT_ID / RAVEL_AGENT_KEY are empty. Register first:\n"
                 "  python -m ravel_adapter.register ravel")
    logging.info("serving as ravel on %s (Ravel at %s)", config.SWITCH_URL, config.RAVEL_DIR)
    client = SwitchClient(
        config.SWITCH_URL, config.RAVEL_AGENT_ID, config.RAVEL_AGENT_KEY,
        handler=lambda body, sender: ravel.handle(body, sender=sender),
        state_path=config.ROOT / ".ravel_state.json")
    client.run_forever()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        local_test(" ".join(sys.argv[1:]))
    else:
        serve()
