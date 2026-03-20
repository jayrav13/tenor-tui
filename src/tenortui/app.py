import argparse
import sys

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical

from tenortui.config import load_config
from tenortui.exceptions import ConfigError, ProviderError, SymbolNotFoundError
from tenortui.providers import PROVIDERS
from tenortui.widgets.chain_table import ChainTable
from tenortui.widgets.expiry_selector import ExpirySelector
from tenortui.widgets.status_bar import StatusBar
from tenortui.widgets.ticker_bar import TickerBar


class TenorTUI(App):
    CSS_PATH = "styles/app.tcss"
    TITLE = "TenorTUI"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("slash", "focus_search", "Search"),
        ("s", "focus_search", "Search"),
        ("ctrl+r", "refresh", "Refresh"),
    ]

    def __init__(self, provider):
        super().__init__()
        self._provider = provider
        self._current_symbol: str | None = None
        self._current_expiration: str | None = None
        self._current_price: float | None = None

    def compose(self) -> ComposeResult:
        yield TickerBar()
        with Vertical(id="main-content"):
            yield ExpirySelector()
            yield ChainTable()
        yield StatusBar(provider_name=self._provider.name)

    def on_mount(self) -> None:
        self.query_one(TickerBar).focus_input()

    def on_ticker_bar_ticker_submitted(self, event: TickerBar.TickerSubmitted) -> None:
        self._current_symbol = event.symbol
        self._load_ticker(event.symbol)

    def on_expiry_selector_expiry_selected(self, event: ExpirySelector.ExpirySelected) -> None:
        self._current_expiration = event.expiration
        if self._current_symbol:
            self._load_chain(self._current_symbol, event.expiration)

    def action_focus_search(self) -> None:
        self.query_one(TickerBar).focus_input()

    def action_refresh(self) -> None:
        if self._current_symbol:
            self._load_ticker(self._current_symbol)

    @work(exclusive=True, thread=True)
    def _load_ticker(self, symbol: str) -> None:
        ticker_bar = self.query_one(TickerBar)
        expiry_selector = self.query_one(ExpirySelector)
        chain_table = self.query_one(ChainTable)

        self.call_from_thread(setattr, chain_table, "loading", True)

        try:
            quote = self._provider.get_quote(symbol)
            self._current_price = quote.price
            self.call_from_thread(ticker_bar.show_quote, quote)
        except SymbolNotFoundError:
            self.call_from_thread(ticker_bar.show_error, f"Symbol '{symbol}' not found")
            self.call_from_thread(setattr, chain_table, "loading", False)
            return
        except ProviderError as e:
            self.call_from_thread(ticker_bar.show_error, str(e))
            self.call_from_thread(setattr, chain_table, "loading", False)
            return

        try:
            expirations = self._provider.get_expirations(symbol)
            self.call_from_thread(expiry_selector.set_expirations, expirations)

            if expirations:
                self._current_expiration = expirations[0]
                chain = self._provider.get_chain(symbol, expirations[0])
                self.call_from_thread(chain_table.display_chain, chain, self._current_price)
            else:
                self.call_from_thread(chain_table.show_message, f"No options available for {symbol}")
        except ProviderError as e:
            self.call_from_thread(chain_table.show_message, str(e))

        self.call_from_thread(setattr, chain_table, "loading", False)
        status_bar = self.query_one(StatusBar)
        self.call_from_thread(status_bar.update_refresh_time)

    @work(exclusive=True, thread=True, group="chain")
    def _load_chain(self, symbol: str, expiration: str) -> None:
        chain_table = self.query_one(ChainTable)

        self.call_from_thread(setattr, chain_table, "loading", True)

        try:
            chain = self._provider.get_chain(symbol, expiration)
            self.call_from_thread(chain_table.display_chain, chain, self._current_price)
        except ProviderError as e:
            self.call_from_thread(chain_table.show_message, str(e))

        self.call_from_thread(setattr, chain_table, "loading", False)
        status_bar = self.query_one(StatusBar)
        self.call_from_thread(status_bar.update_refresh_time)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tenortui",
        description="Terminal UI for browsing stock options chains",
        epilog="Provider config in ~/.tenorrc:\n  yahoo: no config needed\n  tradier: requires 'api_key', optional 'sandbox' (default: false)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        choices=list(PROVIDERS.keys()),
        default=None,
        help="Data provider to use (overrides ~/.tenorrc)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    try:
        config = load_config(provider_override=args.provider)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    provider_cls = PROVIDERS[config.provider_name]

    if config.provider_name == "tradier":
        provider = provider_cls(
            api_key=config.provider_config["api_key"],
            sandbox=config.provider_config.get("sandbox", False),
        )
    else:
        provider = provider_cls()

    app = TenorTUI(provider=provider)
    app.run()
