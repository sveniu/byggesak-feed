import json
import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)


def load_state(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"seen_journal_ids": [], "feeds": {}}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
        log.info("State saved to %s", path)
    except BaseException:
        os.unlink(tmp)
        raise
