"""Screen: edit an entry's tags."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from .. import library


class EditTagsScreen(ModalScreen[list[str] | None]):
    """Edit an entry's tags as a comma-separated list.

    Saves to disk and dismisses with the new tags, or dismisses with
    *None* if the user cancels.
    """

    DEFAULT_CSS = """
    EditTagsScreen {
        align: center middle;
    }

    #tags-dialog {
        width: 80%;
        max-width: 80;
        height: auto;
        border: round $accent;
        background: $panel;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self, entry: dict[str, Any]) -> None:
        super().__init__()
        self._entry = entry

    def compose(self) -> ComposeResult:
        with Vertical(id="tags-dialog"):
            yield Static(f"Tags for: {self._entry.get('title', '(untitled)')}")
            yield Input(
                value=", ".join(self._entry.get("tags", [])),
                placeholder="comma, separated, tags",
                id="tags_input",
            )

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        tags = library.parse_tags(event.value)
        self._entry["tags"] = tags
        library.save_entry(self._entry)
        self.dismiss(tags)

    def action_cancel(self) -> None:
        self.dismiss(None)
