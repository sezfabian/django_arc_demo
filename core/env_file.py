"""Load key=value pairs from a .env file into os.environ (no extra dependency)."""

from __future__ import annotations

import os
from pathlib import Path



def load_env_file(path: Path) -> None:
    """Populate os.environ from *path* if it exists. Existing env vars are not overwritten."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
