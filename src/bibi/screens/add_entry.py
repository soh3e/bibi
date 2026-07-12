"""Screen: choose which kind of entry to add."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ..vim import VimButtonBindings


class AddEntryScreen(VimButtonBindings, ModalScreen[str | None]):
    """Ask which importer to use.

    Dismisses with ``"arxiv"``, ``"pdf"``, or *None* if cancelled.
    """

    DEFAULT_CSS = """
    AddEntryScreen {
        align: center middle;
    }

    #add-entry-dialog {
        width: auto;
        max-width: 80;
        height: auto;
        border: round $accent;
        background: $panel;
        padding: 1 2;
    }

    #add-entry-buttons {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    #add-entry-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        *VimButtonBindings.BINDINGS,
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("a", "choose_arxiv", "arXiv", show=True),
        Binding("p", "choose_pdf", "PDF", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="add-entry-dialog"):
            yield Static("Add an entry from:")
            with Horizontal(id="add-entry-buttons"):
                yield Button("arXiv [a]", id="arxiv", variant="primary")
                yield Button("PDF [p]", id="pdf", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)

    def action_choose_arxiv(self) -> None:
        self.dismiss("arxiv")

    def action_choose_pdf(self) -> None:
        self.dismiss("pdf")

    def action_cancel(self) -> None:
        self.dismiss(None)
