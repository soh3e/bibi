"""Shared vim-style scroll keybinds (j/k/gg/G) for screens with a scrollable
preview pane."""

from __future__ import annotations

import time

from textual import events
from textual.binding import Binding
from textual.widget import Widget

_DOUBLE_TAP_WINDOW = 0.6  # seconds allowed between the two 'g' presses of 'gg'


class VimScrollBindings:
    """Mixin for a :class:`~textual.screen.Screen` with one scrollable pane.

    Subclasses must implement :meth:`vim_scroll_target` to return the widget
    that ``j``/``k``/``gg``/``G`` should scroll.
    """

    BINDINGS = [
        Binding("j", "vim_scroll_down", "Down", show=False),
        Binding("k", "vim_scroll_up", "Up", show=False),
        Binding("G", "vim_scroll_bottom", "Bottom", show=False),
    ]

    _vim_last_g_time: float = 0.0

    def vim_scroll_target(self) -> Widget:
        raise NotImplementedError

    def action_vim_scroll_down(self) -> None:
        self.vim_scroll_target().scroll_down()

    def action_vim_scroll_up(self) -> None:
        self.vim_scroll_target().scroll_up()

    def action_vim_scroll_bottom(self) -> None:
        self.vim_scroll_target().scroll_end()

    def on_key(self, event: events.Key) -> None:
        if event.character != "g":
            return

        now = time.monotonic()
        if now - self._vim_last_g_time < _DOUBLE_TAP_WINDOW:
            self._vim_last_g_time = 0.0
            event.stop()
            self.vim_scroll_target().scroll_home()
        else:
            self._vim_last_g_time = now
