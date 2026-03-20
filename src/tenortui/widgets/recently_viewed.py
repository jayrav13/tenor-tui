from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Static, Label

from tenortui.models import Quote
from tenortui.widgets.ticker_bar import TickerBar


class RecentlyViewed(Widget):
    DEFAULT_CSS = """
    RecentlyViewed {
        height: 1fr;
    }
    RecentlyViewed .rv-title {
        text-style: bold;
        padding: 1 1 0 1;
        color: $text;
    }
    RecentlyViewed .rv-loading {
        padding: 0 1;
        color: $text-muted;
    }
    RecentlyViewed ListView {
        height: auto;
        max-height: 100%;
        padding: 0 1;
    }
    RecentlyViewed ListItem {
        height: 1;
        padding: 0 1;
    }
    RecentlyViewed .rv-empty {
        padding: 1;
        color: $text-muted;
        content-align: center middle;
        height: 1fr;
    }
    """

    def __init__(self, symbols: list[str] | None = None) -> None:
        super().__init__()
        self._symbols = symbols or []
        self._quotes: list[Quote] = []
        self._has_history = bool(self._symbols)

    def compose(self) -> ComposeResult:
        if not self._symbols:
            yield Static("Search for a ticker to view options chain", classes="rv-empty")
            return
        yield Static("Recently Viewed", classes="rv-title")
        yield Static("Loading quotes...", classes="rv-loading", id="rv-loading")
        yield ListView()

    def update_quotes(self, quotes: list[Quote]) -> None:
        self._quotes = quotes
        if self._has_history:
            self.query_one("#rv-loading", Static).display = False
            list_view = self.query_one(ListView)
            list_view.clear()
            for quote in quotes:
                change_sign = "+" if quote.change >= 0 else ""
                text = (
                    f"{quote.symbol:<6} {quote.name:<30} "
                    f"${quote.price:>10.2f}  "
                    f"{change_sign}{quote.change:.2f} ({change_sign}{quote.change_percent:.2f}%)"
                )
                list_view.append(ListItem(Label(text)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = self.query_one(ListView).index
        if index is not None and index < len(self._quotes):
            symbol = self._quotes[index].symbol
            self.post_message(TickerBar.TickerSubmitted(symbol))
