"""Screen: add a bibliography entry from an arXiv URL or id."""

from __future__ import annotations

import asyncio
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Input, LoadingIndicator, Static

from .. import arxiv as arxiv_mod
from .. import library
from ..vim import VimButtonBindings, VimScrollBindings


def _format_preview(data: dict[str, Any]) -> str:
    authors = ", ".join(data.get("authors", [])) or "(unknown authors)"
    lines = [
        f"[b]{data.get('title', '(untitled)')}[/b]",
        "",
        authors,
        f"{data.get('year', '?')}  ·  arXiv:{data.get('arxiv_id', '?')}"
        f"  ·  {data.get('primary_category', '?')}",
        "",
        data.get("abstract", ""),
    ]
    return "\n".join(lines)


class AddArxivScreen(VimScrollBindings, VimButtonBindings, ModalScreen[dict | None]):
    """Fetch and confirm an entry from arXiv, dismissing with the saved
    entry dict (or ``None`` if the user cancelled)."""

    DEFAULT_CSS = """
    AddArxivScreen {
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

    #preview-group {
        height: auto;
        max-height: 20;
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
    ]

    def vim_scroll_target(self) -> Widget:
        return self.query_one("#preview-group")

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            with Vertical(id="input-group"):
                yield Static("Add entry from arXiv URL or id:")
                yield Input(placeholder="https://arxiv.org/abs/2301.00001 or 2301.00001",
                            id="url_input")
                yield Static("", id="error_msg", classes="error")
            yield LoadingIndicator(id="loading-group")
            with VerticalScroll(id="preview-group"):
                yield Static(id="preview_text")
                with Horizontal(id="button-row"):
                    yield Button("Cancel [esc]", id="cancel", variant="error")
                    yield Button("Save [enter]", id="confirm", variant="success")

    def on_mount(self) -> None:
        self._fetched_data: dict[str, Any] | None = None
        self._fetched_pdf: bytes | None = None
        self._set_state("input")

    def _set_state(self, state: str) -> None:
        self.query_one("#input-group").display = state == "input"
        self.query_one("#loading-group").display = state == "loading"
        self.query_one("#preview-group").display = state == "preview"

        if state == "input":
            self.query_one("#url_input", Input).focus()
        elif state == "preview":
            self.query_one("#confirm", Button).focus()

    def _show_error(self, message: str) -> None:
        self.query_one("#error_msg", Static).update(message)
        self._set_state("input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value
        arxiv_id = arxiv_mod.parse_arxiv_input(raw)
        if arxiv_id is None:
            self._show_error(f"Doesn't look like an arXiv URL or id: '{raw}'")
            return

        self.query_one("#error_msg", Static).update("")
        self._set_state("loading")
        self.do_fetch(arxiv_id)

    @work(exclusive=True)
    async def do_fetch(self, arxiv_id: str) -> None:
        data = await asyncio.to_thread(arxiv_mod.fetch_entry, arxiv_id)
        if data is None:
            self._show_error(f"No arXiv entry found for '{arxiv_id}'.")
            return

        pdf_bytes = None
        try:
            import requests
            response = await asyncio.to_thread(requests.get, data["pdf_url"], timeout=30)
            if response.ok:
                pdf_bytes = response.content
        except Exception:
            pdf_bytes = None

        self._fetched_data = data
        self._fetched_pdf = pdf_bytes
        self.query_one("#preview_text", Static).update(_format_preview(data))
        self._set_state("preview")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.action_cancel()
        elif event.button.id == "confirm":
            self.action_confirm()

    def action_confirm(self) -> None:
        if self._fetched_data is None:
            return

        folder = library.create_entry(self._fetched_data, self._fetched_pdf)
        entry = dict(self._fetched_data)
        entry["_folder"] = str(folder)
        self.dismiss(entry)

    def action_cancel(self) -> None:
        self.dismiss(None)
