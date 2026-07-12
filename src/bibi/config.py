"""bibi's user config file, ``~/.config/bibi/config.toml``.

Currently the only setting is ``library_dir``, which says where entry
folders are stored. There's no built-in default -- run ``bibi init`` to
set one, or set the ``$BIBI_LIBRARY_DIR`` env var.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".config" / "bibi" / "config.toml"


class NotConfigured(RuntimeError):
    """Raised when no library directory has been set up yet."""


def _load() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}

    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def is_configured() -> bool:
    """Whether a library directory is available via env var or config file."""
    return bool(os.environ.get("BIBI_LIBRARY_DIR") or _load().get("library_dir"))


def get_library_dir() -> Path:
    """Resolve the library directory, creating it if needed.

    Precedence: the ``$BIBI_LIBRARY_DIR`` env var, then ``library_dir`` in
    :data:`CONFIG_PATH`.

    :raises NotConfigured: if neither is set.
    """
    override = os.environ.get("BIBI_LIBRARY_DIR")
    if override:
        library_dir = Path(override).expanduser()
    else:
        configured = _load().get("library_dir")
        if not configured:
            raise NotConfigured(
                "bibi isn't set up yet -- run `bibi init` to choose where "
                "your library should live."
            )
        library_dir = Path(configured).expanduser()

    library_dir.mkdir(parents=True, exist_ok=True)
    return library_dir


def write_library_dir(path: Path) -> None:
    """Write *path* as ``library_dir`` to :data:`CONFIG_PATH`."""
    import json

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(f"library_dir = {json.dumps(str(path))}\n")
