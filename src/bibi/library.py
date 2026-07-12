"""On-disk storage for bibi entries.

Papis-style library: each entry is a folder containing ``info.yaml`` plus
any downloaded files. Folder names are opaque (random hex) -- the TUI is
meant to be the only interface anyone needs, so a human-readable name buys
nothing and a random one sidesteps collisions/slugification entirely.
"""

from __future__ import annotations

import os
import shutil
import uuid
import webbrowser
from pathlib import Path
from typing import Any

import yaml

from .config import get_library_dir

INFO_FILE_NAME = "info.yaml"
PDF_FILE_NAME = "paper.pdf"


def _unique_folder(library_dir: Path) -> Path:
    folder = library_dir / uuid.uuid4().hex[:12]
    suffix = 1
    while folder.exists():
        suffix += 1
        folder = library_dir / f"{uuid.uuid4().hex[:12]}-{suffix}"
    return folder


def _write_info(folder: Path, data: dict[str, Any]) -> None:
    with open(folder / INFO_FILE_NAME, "w") as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False,
                        sort_keys=False)


def create_entry(data: dict[str, Any], pdf_bytes: bytes | None = None) -> Path:
    """Save *data* (and optionally a PDF) as a new library entry.

    :returns: the path to the new entry's folder.
    """
    library_dir = get_library_dir()
    folder = _unique_folder(library_dir)
    folder.mkdir(parents=True)

    data = dict(data)
    if pdf_bytes:
        (folder / PDF_FILE_NAME).write_bytes(pdf_bytes)
        data["files"] = [PDF_FILE_NAME]

    _write_info(folder, data)
    return folder


def save_entry(entry: dict[str, Any]) -> None:
    """Persist an existing entry's current fields back to its ``info.yaml``."""
    folder = entry.get("_folder")
    if not folder:
        raise ValueError("Entry has no folder to save to.")

    data = {key: value for key, value in entry.items() if key != "_folder"}
    _write_info(Path(folder), data)


def delete_entry(entry: dict[str, Any]) -> None:
    """Permanently delete an entry's folder and everything in it."""
    folder = entry.get("_folder")
    if not folder:
        raise ValueError("Entry has no folder to delete.")

    shutil.rmtree(folder)


def parse_tags(raw: str) -> list[str]:
    """Parse a comma-separated tags string into a deduplicated list."""
    seen: set[str] = set()
    tags = []
    for part in raw.split(","):
        tag = part.strip()
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def list_entries() -> list[dict[str, Any]]:
    """List all entries in the library, newest first."""
    library_dir = get_library_dir()

    entries = []
    for info_path in library_dir.glob(f"*/{INFO_FILE_NAME}"):
        with open(info_path) as f:
            data = yaml.safe_load(f) or {}
        data["_folder"] = str(info_path.parent)
        entries.append(data)

    entries.sort(key=lambda e: os.path.getmtime(e["_folder"]), reverse=True)
    return entries


def get_entry_file(entry: dict[str, Any]) -> Path | None:
    """Return the absolute path to an entry's attached file, if any."""
    files = entry.get("files")
    folder = entry.get("_folder")
    if not files or not folder:
        return None

    path = Path(folder) / files[0]
    return path if path.exists() else None


def open_entry_file(entry: dict[str, Any]) -> bool:
    """Open an entry's file in the system's default browser.

    Passes ``new=0`` to ask the browser to reuse an existing window/tab
    rather than spawn a new one -- whether that's honored is up to the
    browser itself.

    :returns: *False* if the entry has no attached file to open.
    :raises webbrowser.Error: if no browser could be found to open it with.
    """
    path = get_entry_file(entry)
    if path is None:
        return False

    webbrowser.open(path.as_uri(), new=0)
    return True


def get_entry_link(entry: dict[str, Any]) -> str | None:
    """Return the link that :func:`open_entry_file` would open, as a string.

    Prefers the local file (as a ``file://`` URI); falls back to the
    entry's source URL (e.g. the arXiv abstract page) if there's no
    attached file.
    """
    path = get_entry_file(entry)
    if path is not None:
        return path.as_uri()

    return entry.get("url")
