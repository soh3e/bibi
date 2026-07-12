"""Clipboard support.

Textual's `App.copy_to_clipboard` writes an OSC 52 escape sequence, but
plenty of terminals (notably GNOME Terminal/Console and other VTE-based
terminals) don't support the write side of OSC 52 at all. Prefer shelling
out to a real clipboard utility when one is available, and only fall back
to OSC 52 if none is found (e.g. a remote session with no local tool).
"""

from __future__ import annotations

import shutil
import subprocess

from textual.app import App

_SYSTEM_CLIPBOARD_COMMANDS = [
    ["wl-copy"],
    ["xclip", "-selection", "clipboard"],
    ["xsel", "--clipboard", "--input"],
    ["pbcopy"],
]


def copy(app: App, text: str) -> None:
    """Copy *text* to the clipboard, preferring a system tool over OSC 52."""
    for command in _SYSTEM_CLIPBOARD_COMMANDS:
        if shutil.which(command[0]) is None:
            continue

        try:
            subprocess.run(command, input=text.encode(), check=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            continue
        else:
            return

    app.copy_to_clipboard(text)
