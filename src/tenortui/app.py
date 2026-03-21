import argparse
import asyncio
import sys

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical

from tenortui.config import load_config
from tenortui.exceptions import ConfigError, ProviderError, SymbolNotFoundError
from tenortui.history import load_history, add_to_history
from tenortui.providers import PROVIDERS
from tenortui.providers.yahoo import batch_quotes
from tenortui.widgets.chain_table import ChainTable
from tenortui.widgets.command_palette import CommandPalette
from tenortui.widgets.expiry_selector import ExpirySelector
from tenortui.widgets.help_overlay import HelpOverlay
from tenortui.widgets.recently_viewed import RecentlyViewed
from tenortui.widgets.status_bar import StatusBar
from tenortui.widgets.ticker_bar import TickerBar


class TenorTUI(App):
    CSS_PATH = "styles/app.tcss"
    TITLE = "TenorTUI"
    AUTO_FOCUS = None
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
        self._loading_ticker: bool = False
        self._history = load_history()

    def compose(self) -> ComposeResult:
        yield TickerBar()
        with Vertical(id="main-content"):
            yield ExpirySelector()
            yield RecentlyViewed(symbols=self._history)
            yield ChainTable()
        yield StatusBar(provider_name=self._provider.name)
        yield CommandPalette()

    def on_mount(self) -> None:
        chain_table = self.query_one(ChainTable)
        recently_viewed = self.query_one(RecentlyViewed)
        if self._history:
            chain_table.display = False
            self._fetch_recent_quotes()
        else:
            recently_viewed.display = False

    def on_ticker_bar_ticker_submitted(self, event: TickerBar.TickerSubmitted) -> None:
        self._current_symbol = event.symbol
        self._load_ticker(event.symbol)

    def on_expiry_selector_expiry_selected(
        self, event: ExpirySelector.ExpirySelected
    ) -> None:
        self._current_expiration = event.expiration
        if self._current_symbol and not self._loading_ticker:
            self._load_chain(self._current_symbol, event.expiration)

    def action_focus_search(self) -> None:
        self.query_one(TickerBar).focus_input()

    def action_refresh(self) -> None:
        if self._current_symbol:
            self._load_ticker(self._current_symbol)

    def action_help(self) -> None:
        self.push_screen(HelpOverlay())

    def action_command_palette(self) -> None:
        self.query_one(CommandPalette).open()

    def _input_has_focus(self) -> bool:
        """Check if any text input widget has focus."""
        focused = self.focused
        if focused is None:
            return False
        from textual.widgets import Input

        return isinstance(focused, Input)

    def on_key(self, event) -> None:
        """Handle vim-style navigation keys when no input is focused."""
        if self._input_has_focus():
            return

        from textual.widgets import DataTable, ListView

        key = event.key

        if key == "question_mark":
            self.action_help()
            event.prevent_default()
        elif key == "colon":
            self.action_command_palette()
            event.prevent_default()
        elif key == "j":
            if isinstance(self.focused, DataTable):
                self.focused.action_cursor_down()
                event.prevent_default()
            elif isinstance(self.focused, ListView):
                self.focused.action_cursor_down()
                event.prevent_default()
        elif key == "k":
            if isinstance(self.focused, DataTable):
                self.focused.action_cursor_up()
                event.prevent_default()
            elif isinstance(self.focused, ListView):
                self.focused.action_cursor_up()
                event.prevent_default()
        elif key == "g":
            if isinstance(self.focused, DataTable):
                self.focused.move_cursor(row=0)
                event.prevent_default()
            elif isinstance(self.focused, ListView):
                self.focused.index = 0
                event.prevent_default()
        elif key == "G":
            if isinstance(self.focused, DataTable):
                self.focused.move_cursor(row=self.focused.row_count - 1)
                event.prevent_default()
            elif isinstance(self.focused, ListView):
                count = len(self.focused.children)
                if count > 0:
                    self.focused.index = count - 1
                event.prevent_default()
        elif key == "l":
            self.action_focus_next()
            event.prevent_default()
        elif key == "h":
            self.action_focus_previous()
            event.prevent_default()
        elif key == "r":
            self.action_refresh()
            event.prevent_default()

    def on_command_palette_command_submitted(
        self, event: CommandPalette.CommandSubmitted
    ) -> None:
        """Handle commands from the command palette."""
        cmd = event.command.lower().strip()
        if cmd in ("q", "quit"):
            self.exit()
        elif cmd == "help":
            self.action_help()
        elif cmd.startswith("search ") or cmd.startswith("s "):
            parts = cmd.split(None, 1)
            if len(parts) == 2:
                symbol = parts[1].strip().upper()
                self._current_symbol = symbol
                self._load_ticker(symbol)

    @work(exclusive=True, group="recent")
    async def _fetch_recent_quotes(self) -> None:
        quotes = await asyncio.to_thread(batch_quotes, self._history)
        self.query_one(RecentlyViewed).update_quotes(quotes)

    @work(exclusive=True, group="ticker")
    async def _load_ticker(self, symbol: str) -> None:
        ticker_bar = self.query_one(TickerBar)
        expiry_selector = self.query_one(ExpirySelector)
        chain_table = self.query_one(ChainTable)

        chain_table.loading = True
        self._loading_ticker = True

        recently_viewed = self.query_one(RecentlyViewed)
        recently_viewed.display = False
        chain_table.display = True

        try:
            quote = await asyncio.to_thread(self._provider.get_quote, symbol)
            self._current_price = quote.price
            ticker_bar.show_quote(quote)
            self._history = add_to_history(symbol)
        except SymbolNotFoundError:
            ticker_bar.show_error(f"Symbol '{symbol}' not found")
            chain_table.loading = False
            self._loading_ticker = False
            return
        except ProviderError as e:
            ticker_bar.show_error(str(e))
            chain_table.loading = False
            self._loading_ticker = False
            return

        try:
            expirations = await asyncio.to_thread(
                self._provider.get_expirations, symbol
            )
            await expiry_selector.set_expirations(expirations)

            if expirations:
                self._current_expiration = expirations[0]
                chain = await asyncio.to_thread(
                    self._provider.get_chain, symbol, expirations[0]
                )
                await chain_table.display_chain(chain, self._current_price)
            else:
                await chain_table.show_message(f"No options available for {symbol}")
        except ProviderError as e:
            await chain_table.show_message(str(e))

        chain_table.loading = False
        self._loading_ticker = False
        self.query_one(StatusBar).update_refresh_time()

    @work(exclusive=True, group="chain")
    async def _load_chain(self, symbol: str, expiration: str) -> None:
        chain_table = self.query_one(ChainTable)

        chain_table.loading = True

        try:
            chain = await asyncio.to_thread(
                self._provider.get_chain, symbol, expiration
            )
            await chain_table.display_chain(chain, self._current_price)
        except ProviderError as e:
            await chain_table.show_message(str(e))

        chain_table.loading = False
        self.query_one(StatusBar).update_refresh_time()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tenortui",
        description="Terminal UI for browsing stock options chains",
        epilog="Provider config in ~/.config/tenor/config.yaml:\n  yahoo: no config needed\n  tradier: requires 'api_key', optional 'sandbox' (default: false)",
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
