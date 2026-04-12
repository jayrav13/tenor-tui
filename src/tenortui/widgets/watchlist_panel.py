# src/tenortui/widgets/watchlist_panel.py
from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView, Static

from tenortui.models import OptionContract, Quote
from tenortui.watchlists import WatchlistData, WatchlistItem


class WatchlistPanel(Widget):
    DEFAULT_CSS = """
    WatchlistPanel {
        height: 1fr;
    }
    WatchlistPanel .wl-tab-bar {
        height: 1;
        padding: 0 1;
    }
    WatchlistPanel .wl-tab {
        min-width: 8;
        height: 1;
        margin: 0 1 0 0;
        background: $surface;
        color: $text-muted;
    }
    WatchlistPanel .wl-tab.active {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    WatchlistPanel ListView {
        height: auto;
        max-height: 100%;
        padding: 0 1;
    }
    WatchlistPanel ListItem {
        height: 1;
        padding: 0 1;
    }
    WatchlistPanel .wl-empty {
        padding: 1;
        color: $text-muted;
        content-align: center middle;
        height: 1fr;
    }
    WatchlistPanel .wl-loading {
        padding: 0 1;
        color: $text-muted;
    }
    WatchlistPanel .wl-contract {
        color: $text-muted;
    }
    WatchlistPanel .wl-contract-warning {
        color: yellow;
    }
    """

    class TickerSelected(Message):
        def __init__(self, symbol: str) -> None:
            self.symbol = symbol
            super().__init__()

    class WatchlistChanged(Message):
        def __init__(self, index: int) -> None:
            self.index = index
            super().__init__()

    SORT_KEYS = [None, "symbol", "price", "change", "volume"]

    def __init__(self) -> None:
        super().__init__()
        self._watchlist_data: WatchlistData | None = None
        self._active_index: int = 0
        self._equity_quotes: dict[str, Quote] = {}
        self._contract_quotes: dict[tuple[str, str], list[OptionContract]] = {}
        self._flat_items: list[WatchlistItem] = []
        self._sort_key: str | None = None

    def compose(self) -> ComposeResult:
        yield Horizontal(classes="wl-tab-bar")
        yield Static("Loading...", classes="wl-loading", id="wl-loading")
        yield ListView()
        yield Static(
            "Press w to add a ticker to your watchlist",
            classes="wl-empty",
            id="wl-empty",
        )

    def set_watchlists(self, data: WatchlistData) -> None:
        self._watchlist_data = data
        self._active_index = data.active_index
        self._rebuild_tabs()
        self._rebuild_list()

    def _rebuild_tabs(self) -> None:
        if self._watchlist_data is None:
            return
        tab_bar = self.query_one(".wl-tab-bar", Horizontal)
        tab_bar.remove_children()
        for i, wl in enumerate(self._watchlist_data.watchlists):
            classes = "wl-tab active" if i == self._active_index else "wl-tab"
            btn = Button(wl.name, classes=classes, id=f"wl-tab-{i}")
            tab_bar.mount(btn)

    def _rebuild_list(self) -> None:
        if self._watchlist_data is None:
            return
        wl = self._watchlist_data.watchlists[self._active_index]
        list_view = self.query_one(ListView)
        list_view.clear()
        loading = self.query_one("#wl-loading", Static)
        empty = self.query_one("#wl-empty", Static)

        if not wl.items:
            loading.display = False
            empty.display = True
            list_view.display = False
            return

        empty.display = False
        list_view.display = True

        self._flat_items = []
        groups = self._build_display_groups(wl.items, sort_key=self._sort_key)

        for symbol, items in groups:
            for item in items:
                self._flat_items.append(item)
                if item.type == "equity":
                    quote = self._equity_quotes.get(symbol)
                    if quote:
                        change_sign = "+" if quote.change >= 0 else ""
                        text = (
                            f"{quote.symbol:<6} "
                            f"${quote.price:>10.2f}  "
                            f"{change_sign}{quote.change:.2f} "
                            f"({change_sign}{quote.change_percent:.2f}%)"
                        )
                    else:
                        text = f"{symbol}"
                    list_view.append(ListItem(Label(text)))
                else:
                    dte = self._calculate_dte(item.expiration) if item.expiration else 0
                    contract = self._find_contract_quote(item)
                    dte_str = f"DTE: {dte}"
                    warning = dte <= 7
                    if contract:
                        text = (
                            f"  {item.strike:.0f}"
                            f"{'P' if item.option_type == 'put' else 'C'} "
                            f"{item.expiration[5:] if item.expiration else ''}  "
                            f"{contract.bid:.2f}/{contract.ask:.2f}  "
                            f"mid {contract.mid:.2f}  "
                            f"{dte_str}"
                        )
                    else:
                        type_char = "P" if item.option_type == "put" else "C"
                        text = (
                            f"  {item.strike:.0f}{type_char} "
                            f"{item.expiration[5:] if item.expiration else ''}  "
                            f"{dte_str}"
                        )
                    cls = "wl-contract-warning" if warning else "wl-contract"
                    list_view.append(ListItem(Label(text, classes=cls)))

        loading.display = False
        if self._flat_items:
            list_view.index = 0

    def _build_display_groups(
        self, items: list[WatchlistItem], sort_key: str | None = None
    ) -> list[tuple[str, list[WatchlistItem]]]:
        groups: dict[str, list[WatchlistItem]] = {}
        order: list[str] = []
        for item in items:
            if item.symbol not in groups:
                groups[item.symbol] = []
                order.append(item.symbol)
            groups[item.symbol].append(item)

        if sort_key == "symbol":
            order.sort()
        elif sort_key == "price":
            order.sort(
                key=lambda s: (
                    self._equity_quotes[s].price if s in self._equity_quotes else 0
                ),
                reverse=True,
            )
        elif sort_key == "change":
            order.sort(
                key=lambda s: (
                    self._equity_quotes[s].change_percent
                    if s in self._equity_quotes
                    else 0
                ),
                reverse=True,
            )
        elif sort_key == "volume":
            order.sort(
                key=lambda s: (
                    self._equity_quotes[s].volume if s in self._equity_quotes else 0
                ),
                reverse=True,
            )

        return [(symbol, groups[symbol]) for symbol in order]

    def cycle_sort(self) -> str | None:
        current_idx = (
            self.SORT_KEYS.index(self._sort_key)
            if self._sort_key in self.SORT_KEYS
            else 0
        )
        self._sort_key = self.SORT_KEYS[(current_idx + 1) % len(self.SORT_KEYS)]
        self._rebuild_list()
        return self._sort_key

    def _calculate_dte(self, expiration: str) -> int:
        exp_date = date.fromisoformat(expiration)
        return (exp_date - date.today()).days

    def _find_contract_quote(self, item: WatchlistItem) -> OptionContract | None:
        if item.expiration is None:
            return None
        contracts = self._contract_quotes.get((item.symbol, item.expiration), [])
        for c in contracts:
            if c.strike == item.strike and c.option_type == item.option_type:
                return c
        return None

    def _get_item_at_flat_index(self, index: int) -> WatchlistItem | None:
        # If _flat_items hasn't been populated yet (e.g. in tests without a running
        # app), derive them directly from _watchlist_data so pure-logic tests work.
        if not self._flat_items and self._watchlist_data is not None:
            wl = self._watchlist_data.watchlists[self._active_index]
            flat: list[WatchlistItem] = []
            for _symbol, items in self._build_display_groups(
                wl.items, sort_key=self._sort_key
            ):
                flat.extend(items)
            if 0 <= index < len(flat):
                return flat[index]
            return None
        if 0 <= index < len(self._flat_items):
            return self._flat_items[index]
        return None

    def get_selected_item(self) -> WatchlistItem | None:
        list_view = self.query_one(ListView)
        if list_view.index is not None:
            return self._get_item_at_flat_index(list_view.index)
        return None

    def update_equity_quotes(self, quotes: list[Quote]) -> None:
        for q in quotes:
            self._equity_quotes[q.symbol] = q
        self._rebuild_list()

    def update_contract_quotes(
        self, contracts: dict[tuple[str, str], list[OptionContract]]
    ) -> None:
        self._contract_quotes.update(contracts)
        self._rebuild_list()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("wl-tab-"):
            index = int(btn_id.split("-")[-1])
            self._active_index = index
            if self._watchlist_data:
                self._watchlist_data.active_index = index
            self._rebuild_tabs()
            self._rebuild_list()
            self.post_message(self.WatchlistChanged(index))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = self.get_selected_item()
        if item and item.type == "equity":
            self.post_message(self.TickerSelected(item.symbol))
