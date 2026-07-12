"""bibi's user config file, ``~/.config/bibi/config.toml``.

Currently the only setting is ``library_dir``, which overrides where entry
folders are stored. Not required to exist -- everything falls back to
sensible defaults.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".config" / "bibi" / "config.toml"

_DEFAULT_LIBRARY_DIR = Path.home() / ".local" / "share" / "bibi" / "library"


def _load() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}

    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def get_library_dir() -> Path:
    """Resolve the library directory, creating it if needed.

    Precedence: the ``$BIBI_LIBRARY_DIR`` env var, then ``library_dir`` in
    :data:`CONFIG_PATH`, then the default under ``~/.local/share/bibi``.
    """
    override = os.environ.get("BIBI_LIBRARY_DIR")
    if override:
        library_dir = Path(override).expanduser()
    else:
        configured = _load().get("library_dir")
        library_dir = Path(configured).expanduser() if configured else _DEFAULT_LIBRARY_DIR

    library_dir.mkdir(parents=True, exist_ok=True)
    return library_dir
