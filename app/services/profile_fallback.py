"""Keeps the last profile read from the database so it stays visible during an outage.

The profile is held in memory per worker and saved as `profile.json` in the snapshot
folder, so a worker started while the database is down can still show it. Projects
are never kept here: during an outage the page says they are unavailable.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from app.schemas.content import PublicProfile

logger = logging.getLogger(__name__)

PROFILE_FILE = "profile.json"

_last_known: PublicProfile | None = None


def remember(profile: PublicProfile | None, snapshot_dir: Path) -> None:
    """Record a profile that was just read from the database."""
    global _last_known
    if profile is None or profile == _last_known:
        return
    _last_known = profile
    try:
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        temporary = snapshot_dir / f".{PROFILE_FILE}.tmp-{os.getpid()}"
        temporary.write_text(profile.model_dump_json(), encoding="utf-8")
        os.replace(temporary, snapshot_dir / PROFILE_FILE)
    except OSError:
        logger.warning("Could not save %s in %s", PROFILE_FILE, snapshot_dir, exc_info=True)


def last_known(snapshot_dir: Path) -> PublicProfile | None:
    """The most recent profile this worker saw, or the one saved on disk."""
    if _last_known is not None:
        return _last_known
    try:
        return PublicProfile.model_validate_json((snapshot_dir / PROFILE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
