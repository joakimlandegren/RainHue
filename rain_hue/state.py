"""Last-decision state file for RainHue.

Both the CLI (cron morning runs) and the API (web UI triggers) write the
last decision here, so the web UI's decision card reflects every run
regardless of which process made it.

Path: $RAINHUE_STATE_FILE, default ~/.rainhue-state.json
"""

import json
import logging
import os

logger = logging.getLogger(__name__)


def state_path() -> str:
    return os.environ.get("RAINHUE_STATE_FILE") or os.path.expanduser("~/.rainhue-state.json")


def write_state(decision: dict) -> None:
    """Persist the last decision atomically (tmp file + rename)."""
    path = state_path()
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(decision, f)
        os.replace(tmp, path)
    except OSError as exc:
        # State is nice-to-have; never break a run because of it.
        logger.warning("could not write state file %s: %s", path, exc)
        try:
            os.unlink(tmp)
        except OSError:
            pass


def read_state() -> dict | None:
    """Read the last decision, or None if missing/corrupt."""
    try:
        with open(state_path()) as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        if not isinstance(exc, FileNotFoundError):
            logger.warning("could not read state file: %s", exc)
        return None
    return data if isinstance(data, dict) else None
