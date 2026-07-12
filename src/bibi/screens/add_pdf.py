"""Screen: add a bibliography entry from a local PDF file or a URL to one."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Input, LoadingIndicator, Static

from .. import library
from ..vim import VimButtonBindings, VimScrollBindings


class AddPdfScreen(VimScrollBindings, VimButtonBindings, ModalScreen[dict | None]):
    """Add an entry from a local PDF path or a URL to one.

    The user explicitly picks which kind of source it is first (no
    guessing based on the string) -- a local path is *moved* into the new
    entry's folder, a URL is downloaded into it. Either way, the user then
    fills in the entry's metadata (only the title is required), and the
    screen dismisses with the saved entry dict (or *None* if cancelled).
    """

    DEFAULT_CSS = """
    AddPdfScreen {
        align: center middle;
    }

    #dialog {
        width: 80%;
        max-width: 100;
        height: auto;
        max-height: 80%;
        border: round $accent;
        background: $panel;
        padding: 1 2;
    }

    .error {
        color: $error;
        height: auto;
    }

    .field-label {
        height: auto;
        margin-top: 1;
    }

    #form-group {
        height: auto;
        max-height: 20;
    }

    #choice-buttons {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    #choice-buttons Button {
        margin: 0 1;
    }

    #button-row {
        height: auto;
        margin-top: 1;
        align: right middle;
    }

    #button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        *VimScrollBindings.BINDINGS,
        *VimButtonBindings.BINDINGS,
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("f", "choose_local", "Local file", show=True),
        Binding("u", "choose_url", "URL", show=True),
    ]

    def vim_scroll_target(self) -> Widget:
        return self.query_one("#form-group")

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            with Vertical(id="choice-group"):
                yield Static("Add a PDF from:")
                with Horizontal(id="choice-buttons"):
                    yield Button("Local file [f]", id="choice_local", variant="primary")
                    yield Button("URL [u]", id="choice_url", variant="primary")
            with Vertical(id="source-group"):
                yield Static(id="source_label")
                yield Input(id="source_input")
                yield Static("", id="source_error", classes="error")
            yield LoadingIndicator(id="loading-group")
            with VerticalScroll(id="form-group"):
                yield Static("Title (required)", classes="field-label")
                yield Input(placeholder="Title", id="title_input")
                yield Static("Authors (comma-separated)", classes="field-label")
                yield Input(placeholder="e.g. Jane Doe, John Roe", id="authors_input")
                yield Static("Year", classes="field-label")
                yield Input(placeholder="e.g. 2024", id="year_input")
                yield Static("Tags (comma-separated)", classes="field-label")
                yield Input(placeholder="e.g. ml, security", id="tags_input")
                yield Static("", id="form_error", classes="error")
                with Horizontal(id="button-row"):
                    yield Button("Cancel [esc]", id="cancel", variant="error")
                    yield Button("Save", id="confirm", variant="success")

    def on_mount(self) -> None:
        self._source_kind: str | None = None
        self._source_value: Path | str | None = None
        self._pdf_bytes: bytes | None = None
        self._set_state("choice")

    def _set_state(self, state: str) -> None:
        self.query_one("#choice-group").display = state == "choice"
        self.query_one("#source-group").display = state == "source"
        self.query_one("#loading-group").display = state == "loading"
        self.query_one("#form-group").display = state == "form"

        if state == "source":
            self.query_one("#source_input", Input).focus()
        elif state == "form":
            self.query_one("#title_input", Input).focus()

    def action_choose_local(self) -> None:
        self._source_kind = "local"
        self.query_one("#source_label", Static).update("Local PDF file path:")
        source_input = self.query_one("#source_input", Input)
        source_input.placeholder = "~/papers/paper.pdf"
        source_input.value = ""
        self.query_one("#source_error", Static).update("")
        self._set_state("source")

    def action_choose_url(self) -> None:
        self._source_kind = "remote"
        self.query_one("#source_label", Static).update("URL to a PDF:")
        source_input = self.query_one("#source_input", Input)
        source_input.placeholder = "https://example.com/paper.pdf"
        source_input.value = ""
        self.query_one("#source_error", Static).update("")
        self._set_state("source")

    def _show_source_error(self, message: str) -> None:
        self.query_one("#source_error", Static).update(message)
        self._set_state("source")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        if input_id == "source_input":
            self._handle_source_submit(event.value)
        elif input_id == "title_input":
            self.query_one("#authors_input", Input).focus()
        elif input_id == "authors_input":
            self.query_one("#year_input", Input).focus()
        elif input_id == "year_input":
            self.query_one("#tags_input", Input).focus()
        elif input_id == "tags_input":
            self.action_confirm()

    def _handle_source_submit(self, raw: str) -> None:
        raw = raw.strip()
        if not raw:
            self._show_source_error("This can't be empty.")
            return

        if self._source_kind == "local":
            path = Path(raw).expanduser()
            if not path.is_file():
                self._show_source_error(f"No such file: '{raw}'")
                return

            self._source_value = path
            self.query_one("#source_error", Static).update("")
            self._set_state("form")
            return

        self._source_value = raw
        self.query_one("#source_error", Static).update("")
        self._set_state("loading")
        self.do_fetch_remote(raw)

    @work(exclusive=True)
    async def do_fetch_remote(self, url: str) -> None:
        import requests

        try:
            response = await asyncio.to_thread(requests.get, url, timeout=30)
        except requests.RequestException as exc:
            self._show_source_error(f"Couldn't download from '{url}': {exc}")
            return

        if not response.ok or not response.content:
            self._show_source_error(
                f"Couldn't download from '{url}' (status {response.status_code})."
            )
            return

        self._pdf_bytes = response.content
        self._set_state("form")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "choice_local":
            self.action_choose_local()
        elif button_id == "choice_url":
            self.action_choose_url()
        elif button_id == "cancel":
            self.action_cancel()
        elif button_id == "confirm":
            self.action_confirm()

    def action_confirm(self) -> None:
        title = self.query_one("#title_input", Input).value.strip()
        error = self.query_one("#form_error", Static)
        if not title:
            error.update("Title is required.")
            self.query_one("#title_input", Input).focus()
            return

        year_raw = self.query_one("#year_input", Input).value.strip()
        year = None
        if year_raw:
            if not year_raw.isdigit():
                error.update("Year must be a number.")
                self.query_one("#year_input", Input).focus()
                return
            year = int(year_raw)

        authors_raw = self.query_one("#authors_input", Input).value
        authors = [a.strip() for a in authors_raw.split(",") if a.strip()]
        tags = library.parse_tags(self.query_one("#tags_input", Input).value)

        data: dict[str, Any] = {"title": title, "type": "article"}
        if authors:
            data["authors"] = authors
        if year is not None:
            data["year"] = year
        if tags:
            data["tags"] = tags

        if self._source_kind == "remote":
            data["url"] = self._source_value
            folder = library.create_entry(data, self._pdf_bytes)
        else:
            folder = library.create_entry_from_file(data, self._source_value)

        entry = dict(data)
        entry["_folder"] = str(folder)
        self.dismiss(entry)

    def action_cancel(self) -> None:
        self.dismiss(None)
