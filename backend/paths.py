"""Filesystem paths for source defaults and local runtime data."""

import os
import shutil
from pathlib import Path


BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_DATA_DIR = BACKEND_DIR / "default_data"
DATA_DIR = Path(os.getenv("CLAUDE_HUB_DATA_DIR", PROJECT_ROOT / "data")).expanduser()


def data_path(filename: str, seed: bool = True) -> Path:
    """
    Return the writable runtime path for a data file.

    Public repo defaults live in backend/default_data. User/player data lives in
    CLAUDE_HUB_DATA_DIR, or ./data by default, which is intentionally ignored.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / filename
    default = DEFAULT_DATA_DIR / filename

    if seed and not target.exists() and default.exists():
        shutil.copyfile(default, target)

    return target
