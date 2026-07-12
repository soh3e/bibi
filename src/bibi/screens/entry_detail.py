"""Screen: read-only view of a single library entry."""

from __future__ import annotations

import webbrowser
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Static

from .. import clipboard, library
from ..vim import VimScrollBindings
from .confirm_delete import ConfirmDeleteScreen
from .edit_entry import EditEntryScreen
from .edit_tags import EditTagsScreen


def _format_entry(data: dict[str, Any]) -> str:
    authors = ", ".join(data.get("authors", [])) or "(unknown authors)"
    lines = [
        f"[b]{data.get('title', '(untitled)')}[/b]",
        "",
        authors,
        f"{data.get('year', '?')}  ·  arXiv:{data.get('arxiv_id', '?')}"
        f"  ·  {data.get('primary_category', '?')}",
        f"[dim]{data.get('url', '')}[/dim]",
    ]
    if data.get("doi"):
        lines.append(f"doi: {data['doi']}")
    if data.get("journal_ref"):
        lines.append(f"journal: {data['journal_ref']}")
    if data.get("files"):
        lines.append(f"files: {', '.join(data['files'])}")
    lines.append(f"tags: {', '.join(data['tags'])}" if data.get("tags") else "tags: (none)")
    lines.append(f"read: {'yes' if data.get('read') else 'no'}")
    lines += ["", data.get("abstract", "")]
    return "\n".join(lines)


class EntryDetailScreen(VimScrollBindings, ModalScreen[None]):
    """Entry viewer, with actions to edit/tag/delete/open it."""

    DEFAULT_CSS = """
    EntryDetailScreen {
        align: center middle;
    }

    #detail-dialog {
        width: 80%;
        max-width: 100;
        height: auto;
        max-height: 80%;
        border: round $accent;
        background: $panel;
        padding: 1 2;
    }
    """

    BINDINGS = [
        *VimScrollBindings.BINDINGS,
        Binding("escape,q,h", "close", "Close", show=True),
        Binding("o", "open_file", "Open", show=True),
        Binding("c", "copy_link", "Copy link", show=True),
        Binding("e", "edit_entry", "Edit entry", show=True),
        Binding("t", "edit_tags", "Edit tags", show=True),
        Binding("d", "delete_entry", "Delete entry", show=True),
    ]

    def __init__(self, entry: dict[str, Any]) -> None:
        super().__init__()
        self._entry = entry

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="detail-dialog"):
            yield Static(_format_entry(self._entry), id="detail_text")

    def vim_scroll_target(self) -> Widget:
        return self.query_one("#detail-dialog")

    def action_close(self) -> None:
        self.dismiss(None)

    def action_open_file(self) -> None:
        try:
            opened = library.open_entry_file(self._entry)
        except webbrowser.Error:
            self.notify("No browser found to open the file with.", severity="error")
            return

        if opened:
            self.notify("Opening in your browser…")
        else:
            self.notify("No file attached to this entry.", severity="warning")

    def action_copy_link(self) -> None:
        link = library.get_entry_link(self._entry)
        if link is None:
            self.notify("Nothing to copy for this entry.", severity="warning")
            return

        clipboard.copy(self.app, link)
        self.notify(f"Copied to clipboard: {link}")

    def action_edit_entry(self) -> None:
        def on_result(updated: dict[str, Any] | None) -> None:
            if updated is not None:
                self.query_one("#detail_text", Static).update(_format_entry(self._entry))

        self.app.push_screen(EditEntryScreen(self._entry), on_result)

    def action_edit_tags(self) -> None:
        def on_result(tags: list[str] | None) -> None:
            if tags is not None:
                self.query_one("#detail_text", Static).update(_format_entry(self._entry))

        self.app.push_screen(EditTagsScreen(self._entry), on_result)

    def action_delete_entry(self) -> None:
        def on_result(confirmed: bool | None) -> None:
            if confirmed:
                library.delete_entry(self._entry)
                self.notify(f"Deleted: {self._entry.get('title', '(untitled)')}")
                self.dismiss(None)

        self.app.push_screen(ConfirmDeleteScreen(self._entry), on_result)
