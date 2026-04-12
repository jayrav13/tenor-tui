# src/tenortui/widgets/watchlist_picker.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from tenortui.watchlists import (
    WatchlistData,
    create_watchlist,
    delete_watchlist,
    rename_watchlist,
)


class WatchlistPicker(ModalScreen[int | None]):
    """Modal to pick which watchlist to add an item to."""

    DEFAULT_CSS = """
    WatchlistPicker {
        align: center middle;
    }
    WatchlistPicker #picker-container {
        width: 40;
        max-height: 60%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    WatchlistPicker .picker-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
        color: $accent;
    }
    WatchlistPicker ListView {
        height: auto;
        max-height: 100%;
    }
    WatchlistPicker ListItem {
        height: 1;
        padding: 0 1;
    }
    WatchlistPicker .picker-footer {
        text-align: center;
        padding: 1 0 0 0;
        color: $text-muted;
    }
    WatchlistPicker #picker-new-input {
        display: none;
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("n", "new_watchlist", "New", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, data: WatchlistData) -> None:
        super().__init__()
        self._watchlist_data = data
        self._creating_new = False

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-container"):
            yield Static("Add to Watchlist", classes="picker-title")
            items = [ListItem(Label(wl.name)) for wl in self._watchlist_data.watchlists]
            yield ListView(*items)
            yield Input(placeholder="New watchlist name", id="picker-new-input")
            yield Static("[n] New  [Esc] Cancel", classes="picker-footer")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self._creating_new:
            index = self.query_one(ListView).index
            self.dismiss(index)

    def action_cancel(self) -> None:
        if self._creating_new:
            self._creating_new = False
            self.query_one("#picker-new-input", Input).display = False
            self.query_one(ListView).focus()
        else:
            self.dismiss(None)

    def action_new_watchlist(self) -> None:
        if self._creating_new:
            return
        self._creating_new = True
        inp = self.query_one("#picker-new-input", Input)
        inp.display = True
        inp.value = ""
        inp.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if name:
            create_watchlist(self._watchlist_data, name)
            new_index = len(self._watchlist_data.watchlists) - 1
            self.dismiss(new_index)

    def action_cursor_down(self) -> None:
        if not self._creating_new:
            self.query_one(ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        if not self._creating_new:
            self.query_one(ListView).action_cursor_up()


class WatchlistManager(ModalScreen[WatchlistData | None]):
    """Modal to manage watchlists (create, rename, delete)."""

    DEFAULT_CSS = """
    WatchlistManager {
        align: center middle;
    }
    WatchlistManager #manager-container {
        width: 45;
        max-height: 70%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    WatchlistManager .manager-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding: 0 0 1 0;
        color: $accent;
    }
    WatchlistManager ListView {
        height: auto;
        max-height: 100%;
    }
    WatchlistManager ListItem {
        height: 1;
        padding: 0 1;
    }
    WatchlistManager .manager-footer {
        text-align: center;
        padding: 1 0 0 0;
        color: $text-muted;
    }
    WatchlistManager #manager-input {
        display: none;
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("n", "new_watchlist", "New", show=False),
        Binding("r", "rename_watchlist", "Rename", show=False),
        Binding("d", "delete_watchlist", "Delete", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self, data: WatchlistData) -> None:
        super().__init__()
        self._watchlist_data = data
        self._editing: str | None = None  # "new" or "rename"

    def compose(self) -> ComposeResult:
        with Vertical(id="manager-container"):
            yield Static("Manage Watchlists", classes="manager-title")
            yield ListView()
            yield Input(placeholder="Watchlist name", id="manager-input")
            yield Static(
                "[n] New  [r] Rename  [d] Delete  [Esc] Close",
                classes="manager-footer",
            )

    def on_mount(self) -> None:
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        lv = self.query_one(ListView)
        lv.clear()
        for wl in self._watchlist_data.watchlists:
            count = len(wl.items)
            label = f"{wl.name} ({count} item{'s' if count != 1 else ''})"
            lv.append(ListItem(Label(label)))

    def action_close(self) -> None:
        if self._editing:
            self._editing = None
            self.query_one("#manager-input", Input).display = False
            self.query_one(ListView).focus()
        else:
            self.dismiss(self._watchlist_data)

    def action_new_watchlist(self) -> None:
        if self._editing:
            return
        self._editing = "new"
        inp = self.query_one("#manager-input", Input)
        inp.display = True
        inp.value = ""
        inp.placeholder = "New watchlist name"
        inp.focus()

    def action_rename_watchlist(self) -> None:
        if self._editing:
            return
        lv = self.query_one(ListView)
        if lv.index is None:
            return
        self._editing = "rename"
        inp = self.query_one("#manager-input", Input)
        inp.display = True
        inp.value = self._watchlist_data.watchlists[lv.index].name
        inp.placeholder = "New name"
        inp.focus()

    def action_delete_watchlist(self) -> None:
        if self._editing:
            return
        lv = self.query_one(ListView)
        if lv.index is None:
            return
        if len(self._watchlist_data.watchlists) <= 1:
            return
        delete_watchlist(self._watchlist_data, lv.index)
        self._rebuild_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if not name:
            return
        if self._editing == "new":
            create_watchlist(self._watchlist_data, name)
        elif self._editing == "rename":
            lv = self.query_one(ListView)
            if lv.index is not None:
                rename_watchlist(self._watchlist_data, lv.index, name)
        self._editing = None
        self.query_one("#manager-input", Input).display = False
        self._rebuild_list()
        self.query_one(ListView).focus()

    def action_cursor_down(self) -> None:
        if not self._editing:
            self.query_one(ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        if not self._editing:
            self.query_one(ListView).action_cursor_up()
