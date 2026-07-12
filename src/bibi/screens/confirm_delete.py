"""Screen: confirm deleting an entry."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ..vim import VimButtonBindings


class ConfirmDeleteScreen(VimButtonBindings, ModalScreen[bool]):
    """Ask for confirmation before deleting an entry.

    Dismisses with *True* to confirm, *False* to cancel.
    """

    DEFAULT_CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }

    #confirm-dialog {
        width: auto;
        max-width: 80;
        height: auto;
        border: round $error;
        background: $panel;
        padding: 1 2;
    }

    #confirm-buttons {
        height: auto;
        margin-top: 1;
        align: right middle;
    }

    #confirm-buttons Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        *VimButtonBindings.BINDINGS,
        Binding("escape,n", "cancel", "Cancel", show=True),
        Binding("y", "confirm", "Delete", show=True),
    ]

    def __init__(self, entry: dict[str, Any]) -> None:
        super().__init__()
        self._entry = entry

    def compose(self) -> ComposeResult:
        title = self._entry.get("title", "(untitled)")
        with Vertical(id="confirm-dialog"):
            yield Static(
                f"Delete \"{title}\"?\n"
                "This also removes its downloaded file, if any. This can't be undone."
            )
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel [n]", id="cancel")
                yield Button("Delete [y]", id="confirm", variant="error")

    def on_mount(self) -> None:
        # default focus is the safe choice, so an accidental Enter doesn't delete
        self.query_one("#cancel", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.action_confirm()
        else:
            self.action_cancel()

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
