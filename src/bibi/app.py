"""bibi: a vim-keybound TUI for bibliography management."""

from __future__ import annotations

import webbrowser
from typing import Any

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Static
from textual.widgets.data_table import RowDoesNotExist

from . import clipboard, library
from .art import BUNNY_LOGO
from .screens.add_arxiv import AddArxivScreen
from .screens.add_entry import AddEntryScreen
from .screens.add_pdf import AddPdfScreen
from .screens.confirm_delete import ConfirmDeleteScreen
from .screens.edit_entry import EditEntryScreen
from .screens.edit_tags import EditTagsScreen
from .screens.entry_detail import EntryDetailScreen

_EMPTY_STATE_TEXT = (
    f"{BUNNY_LOGO}\n\n"
    "Your library is empty.\n"
    "Press 'a' to add your first entry from arXiv."
)

# Layout knobs for the responsive Title/Authors/Tags columns (see
# `BibiApp._rebuild_rows`). Read and Year are small, fixed-width columns.
_READ_COLUMN_WIDTH = 4
_YEAR_COLUMN_WIDTH = 4
_MIN_TITLE_WIDTH = 12
_MIN_AUTHORS_WIDTH = 10
_MIN_TAGS_WIDTH = 6
# 1 padding cell on each side of each of the 5 columns, plus slack for the
# scrollbar so a snug fit doesn't trigger horizontal scrolling.
_CHROME_WIDTH = 2 * 5 + 4


def _truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


def _full_authors(authors: list[str]) -> str:
    return ", ".join(authors) if authors else "(unknown)"


def _full_tags(tags: list[str]) -> str:
    return ", ".join(tags)


def _read_marker(entry: dict[str, Any]) -> str:
    # NOTE: square brackets are Rich/Textual markup syntax, so "[x]" would
    # render as empty (an unclosed style tag named "x") -- escaping the
    # opening bracket keeps it literal.
    return r"\[x]" if entry.get("read") else r"\[ ]"


def _format_authors(authors: list[str], width: int) -> str:
    full = _full_authors(authors)
    if len(full) <= width:
        return full

    if not authors:
        return _truncate(full, width)

    last_name = authors[0].split()[-1] if authors[0].split() else authors[0]
    abbreviated = f"{last_name} et al." if len(authors) > 1 else last_name
    return abbreviated if len(abbreviated) <= width else _truncate(abbreviated, width)


def _allocate_widths(remaining: int, wants: list[tuple[int, int]]) -> list[int]:
    """Split *remaining* width across columns described by (want, minimum).

    Columns are granted their full *want* in ascending order of want --
    the cheapest to satisfy go first -- so only the column(s) that
    genuinely need more room than is available end up truncated. Returns
    widths in the original column order.
    """
    order = sorted(range(len(wants)), key=lambda i: wants[i][0])
    widths = [0] * len(wants)
    left = remaining
    for rank, i in enumerate(order):
        want, minimum = wants[i]
        reserved = sum(wants[j][1] for j in order[rank + 1:])
        width = max(min(want, left - reserved), minimum)
        widths[i] = width
        left -= width
    return widths


class VimDataTable(DataTable):
    """A DataTable with vim-style navigation bound on top of the defaults.

    ``enter`` is repurposed from the default ``select_cursor`` (viewing an
    entry's details, now on ``l`` only) to toggling the Read column instead
    -- overriding it here replaces DataTable's own binding for that key.
    """

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "scroll_top", "Top", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
        Binding("l", "select_cursor", "View", show=False),
        Binding("enter", "app.toggle_read", "Toggle read", show=True),
    ]


class BibiApp(App[None]):
    """Main bibi application: a library list with vim keybinds."""

    TITLE = "bibi"

    CSS = """
    VimDataTable {
        height: 1fr;
    }

    #empty-state {
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("a", "add_entry", "Add entry"),
        Binding("o", "open_file", "Open file"),
        Binding("c", "copy_link", "Copy link"),
        Binding("e", "edit_entry", "Edit entry"),
        Binding("t", "edit_tags", "Edit tags"),
        Binding("d", "delete_entry", "Delete entry"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[dict[str, Any]] = []
        self._entries_by_folder: dict[str, dict[str, Any]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(_EMPTY_STATE_TEXT, id="empty-state")
        yield VimDataTable(cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(VimDataTable).focus()
        self.refresh_table()

    def on_resize(self, event: events.Resize) -> None:
        self._rebuild_rows(event.size.width)

    def refresh_table(self) -> None:
        """Reload entries from disk and rebuild the table."""
        self._entries = library.list_entries()
        self._entries_by_folder = {e["_folder"]: e for e in self._entries}
        self._rebuild_rows(self.size.width)

    def _rebuild_rows(self, total_width: int) -> None:
        """Redraw the table's columns/rows to fit the given terminal width."""
        table = self.query_one(VimDataTable)
        table.display = bool(self._entries)
        self.query_one("#empty-state").display = not self._entries
        if not self._entries:
            table.clear(columns=True)
            return

        title_width, authors_width, tags_width = self._column_widths(self._entries, total_width)

        # `clear()` drops the cursor back to the top row, so remember which
        # entry was selected and restore it once the rows are rebuilt --
        # otherwise a refresh (e.g. after editing tags) silently shifts
        # keyboard actions onto a different entry.
        selected_folder = None
        if table.row_count > 0:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            selected_folder = row_key.value

        table.clear(columns=True)
        table.add_column("Read", width=_READ_COLUMN_WIDTH)
        table.add_column("Title", width=title_width)
        table.add_column("Authors", width=authors_width)
        table.add_column("Tags", width=tags_width)
        table.add_column("Year", width=_YEAR_COLUMN_WIDTH)

        for entry in self._entries:
            read = _read_marker(entry)
            title = _truncate(entry.get("title", "(untitled)"), title_width)
            authors = _format_authors(entry.get("authors", []), authors_width)
            tags = _truncate(_full_tags(entry.get("tags", [])), tags_width)
            table.add_row(read, title, authors, tags, str(entry.get("year", "?")),
                          key=entry["_folder"])

        if selected_folder is not None:
            try:
                table.move_cursor(row=table.get_row_index(selected_folder))
            except RowDoesNotExist:
                pass

    @staticmethod
    def _column_widths(entries: list[dict[str, Any]], total_width: int) -> tuple[int, int, int]:
        """Split the table's width between the Title, Authors and Tags columns.

        Each column gets as much as its longest actual entry needs, so a
        screen with room to spare never truncates anything. When they
        don't all fit, whichever wants *less* space is granted its full
        width first (it's cheap to satisfy), leaving whatever's left to
        the columns that genuinely need more room than is available.
        """
        remaining = total_width - _CHROME_WIDTH - _READ_COLUMN_WIDTH - _YEAR_COLUMN_WIDTH
        remaining = max(remaining, _MIN_TITLE_WIDTH + _MIN_AUTHORS_WIDTH + _MIN_TAGS_WIDTH)

        title_want = max(
            (len(e.get("title") or "(untitled)") for e in entries),
            default=_MIN_TITLE_WIDTH,
        )
        authors_want = max(
            (len(_full_authors(e.get("authors", []))) for e in entries),
            default=_MIN_AUTHORS_WIDTH,
        )
        tags_want = max(
            (len(_full_tags(e.get("tags", []))) for e in entries),
            default=_MIN_TAGS_WIDTH,
        )
        title_want = max(title_want, _MIN_TITLE_WIDTH)
        authors_want = max(authors_want, _MIN_AUTHORS_WIDTH)
        tags_want = max(tags_want, _MIN_TAGS_WIDTH)

        title_width, authors_width, tags_width = _allocate_widths(
            remaining,
            [
                (title_want, _MIN_TITLE_WIDTH),
                (authors_want, _MIN_AUTHORS_WIDTH),
                (tags_want, _MIN_TAGS_WIDTH),
            ],
        )
        return title_width, authors_width, tags_width

    def action_add_entry(self) -> None:
        def on_entry_added(entry: dict[str, Any] | None) -> None:
            if entry is not None:
                self.refresh_table()

        def on_type_chosen(kind: str | None) -> None:
            if kind == "arxiv":
                self.push_screen(AddArxivScreen(), on_entry_added)
            elif kind == "pdf":
                self.push_screen(AddPdfScreen(), on_entry_added)

        self.push_screen(AddEntryScreen(), on_type_chosen)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        folder = event.row_key.value
        entry = self._entries_by_folder.get(folder)
        if entry is not None:
            # tags can be edited from within the detail screen too, so
            # always refresh once it closes.
            self.push_screen(EntryDetailScreen(entry), lambda _: self.refresh_table())

    def _selected_entry(self) -> dict[str, Any] | None:
        table = self.query_one(VimDataTable)
        if table.row_count == 0:
            return None

        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return self._entries_by_folder.get(row_key.value)

    def action_open_file(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return

        try:
            opened = library.open_entry_file(entry)
        except webbrowser.Error:
            self.notify("No browser found to open the file with.", severity="error")
            return

        if opened:
            self.notify("Opening in your browser…")
        else:
            self.notify("No file attached to this entry.", severity="warning")

    def action_copy_link(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return

        link = library.get_entry_link(entry)
        if link is None:
            self.notify("Nothing to copy for this entry.", severity="warning")
            return

        clipboard.copy(self, link)
        self.notify(f"Copied to clipboard: {link}")

    def action_edit_entry(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return

        def on_result(updated: dict[str, Any] | None) -> None:
            if updated is not None:
                self.refresh_table()

        self.push_screen(EditEntryScreen(entry), on_result)

    def action_edit_tags(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return

        def on_result(tags: list[str] | None) -> None:
            if tags is not None:
                self.refresh_table()

        self.push_screen(EditTagsScreen(entry), on_result)

    def action_delete_entry(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return

        def on_result(confirmed: bool | None) -> None:
            if confirmed:
                library.delete_entry(entry)
                self.refresh_table()
                self.notify(f"Deleted: {entry.get('title', '(untitled)')}")

        self.push_screen(ConfirmDeleteScreen(entry), on_result)

    def action_toggle_read(self) -> None:
        entry = self._selected_entry()
        if entry is None:
            return

        entry["read"] = not entry.get("read", False)
        library.save_entry(entry)
        self.refresh_table()


def main() -> None:
    BibiApp().run()


if __name__ == "__main__":
    main()
