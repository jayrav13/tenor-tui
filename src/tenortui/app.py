import argparse
import asyncio
import sys

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical

from tenortui.config import (
    AppConfig,
    GreeksConfig,
    RefreshConfig,
    SpreadThresholds,
    load_config,
    print_config_help,
)
from tenortui.exceptions import ConfigError, ProviderError, SymbolNotFoundError
from tenortui.history import load_history, add_to_history
from tenortui.market_hours import MarketState, get_market_state
from tenortui.providers import PROVIDERS
from tenortui.providers.yahoo import batch_quotes, fetch_fundamentals
from tenortui.risk_free_rate import get_risk_free_rate
from tenortui.widgets.chain_table import ChainTable
from tenortui.widgets.fundamentals_bar import FundamentalsBar
from tenortui.widgets.command_palette import CommandPalette
from tenortui.widgets.expiry_selector import ExpirySelector
from tenortui.widgets.help_overlay import HelpOverlay
from tenortui.widgets.recently_viewed import RecentlyViewed
from tenortui.widgets.settings_screen import SettingsScreen
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
        Binding("ctrl+p", "toggle_auto_refresh", "Pause Refresh", priority=True),
        Binding("comma", "open_settings", "Settings", show=False),
    ]

    def __init__(
        self,
        provider,
        spread_thresholds: SpreadThresholds | None = None,
        greeks_config: GreeksConfig | None = None,
        fred_api_key: str | None = None,
        refresh_config: RefreshConfig | None = None,
        app_config: AppConfig | None = None,
    ):
        super().__init__()
        self._provider = provider
        self._spread_thresholds = spread_thresholds or SpreadThresholds()
        self._greeks_config = greeks_config or GreeksConfig()
        self._refresh_config = refresh_config or RefreshConfig()
        self._current_symbol: str | None = None
        self._current_expiration: str | None = None
        self._current_price: float | None = None
        self._current_dividend_yield: float | None = None
        self._loading_ticker: bool = False
        self._history = load_history()
        self._auto_refresh_enabled: bool = True
        self._auto_refresh_countdown: int = 0
        self._refresh_timer = None
        self._countdown_timer = None
        rate, is_live = get_risk_free_rate(
            fallback=self._greeks_config.risk_free_rate,
            fred_api_key=fred_api_key,
        )
        self._risk_free_rate = rate
        self._risk_free_rate_is_live = is_live
        self._app_config = app_config or AppConfig(
            provider_name=getattr(provider, "name", "yahoo"),
            spread_thresholds=self._spread_thresholds,
            greeks=self._greeks_config,
            fred_api_key=fred_api_key,
            refresh=self._refresh_config,
        )

    def compose(self) -> ComposeResult:
        yield TickerBar()
        with Vertical(id="main-content"):
            yield FundamentalsBar()
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
        self._update_market_display()
        self.query_one(StatusBar).update_rate_display(
            self._risk_free_rate, self._risk_free_rate_is_live
        )
        # Update market state display every 60s
        self.set_interval(60, self._update_market_display)

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

    def action_open_settings(self) -> None:
        self._stop_auto_refresh()
        self.push_screen(
            SettingsScreen(self._app_config),
            callback=self._on_settings_closed,
        )

    def _on_settings_closed(self, result: AppConfig | None) -> None:
        if result is not None:
            old_config = self._app_config
            self._spread_thresholds = result.spread_thresholds
            self._refresh_config = result.refresh
            self._greeks_config = result.greeks
            self._app_config = result
            if result.fred_api_key != old_config.fred_api_key:
                rate, is_live = get_risk_free_rate(
                    fallback=result.greeks.risk_free_rate,
                    fred_api_key=result.fred_api_key,
                )
                self._risk_free_rate = rate
                self._risk_free_rate_is_live = is_live
                self.query_one(StatusBar).update_rate_display(rate, is_live)
            if self._current_symbol and self._current_expiration:
                self._load_chain(self._current_symbol, self._current_expiration)
        if self._auto_refresh_enabled and self._current_symbol:
            self._start_auto_refresh()

    def action_toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh on/off."""
        self._auto_refresh_enabled = not self._auto_refresh_enabled
        if self._auto_refresh_enabled:
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()
            self.query_one(StatusBar).update_refresh_status(paused=True)

    def _get_refresh_interval(self) -> int:
        """Get refresh interval based on market state."""
        state = get_market_state()
        if state == MarketState.REGULAR:
            return self._refresh_config.regular
        elif state in (MarketState.PRE_MARKET, MarketState.AFTER_HOURS):
            return self._refresh_config.extended
        else:
            return self._refresh_config.closed

    def _start_auto_refresh(self) -> None:
        """Start the auto-refresh timer."""
        self._stop_auto_refresh()
        interval = self._get_refresh_interval()
        self._auto_refresh_countdown = interval
        self._refresh_timer = self.set_timer(interval, self._on_auto_refresh)
        self._countdown_timer = self.set_interval(1, self._on_countdown_tick)
        self.query_one(StatusBar).update_refresh_status(seconds_until=interval)

    def _stop_auto_refresh(self) -> None:
        """Stop the auto-refresh timer."""
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer = None
        if self._countdown_timer is not None:
            self._countdown_timer.stop()
            self._countdown_timer = None

    def _on_countdown_tick(self) -> None:
        """Update the countdown display every second."""
        if self._auto_refresh_countdown > 0:
            self._auto_refresh_countdown -= 1
        self.query_one(StatusBar).update_refresh_status(
            seconds_until=self._auto_refresh_countdown
        )

    def _on_auto_refresh(self) -> None:
        """Fired when the auto-refresh timer expires."""
        if self._current_symbol and self._auto_refresh_enabled:
            if self._current_expiration:
                self._load_chain(self._current_symbol, self._current_expiration)
            else:
                self._load_ticker(self._current_symbol)
        # Restart with potentially different interval (market state may have changed)
        if self._auto_refresh_enabled:
            self._start_auto_refresh()

    def _update_market_display(self) -> None:
        """Update the market state in the status bar."""
        self.query_one(StatusBar).update_market_state()

    def _focus_first_table(self) -> None:
        """Focus the first (calls) DataTable so j/k navigation works immediately."""
        from textual.widgets import DataTable

        try:
            tables = self.query_one(ChainTable).query(DataTable)
            if tables:
                tables.first().focus()
        except Exception:
            pass

    def _input_has_focus(self) -> bool:
        """Check if any text input widget has focus."""
        focused = self.focused
        if focused is None:
            return False
        from textual.widgets import Input

        return isinstance(focused, Input)

    def on_key(self, event) -> None:
        """Handle vim-style navigation keys when no input is focused."""
        if isinstance(self.screen, SettingsScreen):
            return
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
        elif cmd == "settings":
            self.action_open_settings()
        elif cmd.startswith("search ") or cmd.startswith("s "):
            parts = cmd.split(None, 1)
            if len(parts) == 2:
                symbol = parts[1].strip().upper()
                self._current_symbol = symbol
                self._load_ticker(symbol)

    @work(exclusive=True, group="recent")
    async def _fetch_recent_quotes(self) -> None:
        quotes = await asyncio.to_thread(batch_quotes, self._history)
        rv = self.query_one(RecentlyViewed)
        rv.update_quotes(quotes)
        from textual.widgets import ListView

        try:
            rv.query_one(ListView).focus()
        except Exception:
            pass

    @work(exclusive=True, group="ticker")
    async def _load_ticker(self, symbol: str) -> None:
        ticker_bar = self.query_one(TickerBar)
        expiry_selector = self.query_one(ExpirySelector)
        chain_table = self.query_one(ChainTable)

        chain_table.loading = True
        self._loading_ticker = True
        self.query_one(FundamentalsBar).hide()

        recently_viewed = self.query_one(RecentlyViewed)
        recently_viewed.display = False
        chain_table.display = True

        try:
            quote = await asyncio.to_thread(self._provider.get_quote, symbol)
            self._current_price = quote.price
            ticker_bar.show_quote(quote)
            self._current_dividend_yield = quote.dividend_yield
            quote = await asyncio.to_thread(fetch_fundamentals, quote)
            self.query_one(FundamentalsBar).show_fundamentals(quote)
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
                if self._greeks_config.enabled and not any(
                    c.has_greeks for c in chain.calls + chain.puts
                ):
                    from tenortui.greeks import calculate_chain_greeks

                    await asyncio.to_thread(
                        calculate_chain_greeks,
                        chain=chain,
                        spot=self._current_price,
                        expiration=expirations[0],
                        risk_free_rate=self._risk_free_rate,
                        dividend_yield=self._current_dividend_yield,
                    )
                await chain_table.display_chain(
                    chain, self._current_price, self._spread_thresholds
                )
            else:
                await chain_table.show_message(f"No options available for {symbol}")
        except ProviderError as e:
            await chain_table.show_message(str(e))

        chain_table.loading = False
        self._loading_ticker = False
        self.query_one(StatusBar).update_refresh_time()
        self._focus_first_table()
        if self._auto_refresh_enabled:
            self._start_auto_refresh()

    @work(exclusive=True, group="chain")
    async def _load_chain(self, symbol: str, expiration: str) -> None:
        chain_table = self.query_one(ChainTable)

        chain_table.loading = True

        try:
            chain = await asyncio.to_thread(
                self._provider.get_chain, symbol, expiration
            )
            if self._greeks_config.enabled and not any(
                c.has_greeks for c in chain.calls + chain.puts
            ):
                from tenortui.greeks import calculate_chain_greeks

                await asyncio.to_thread(
                    calculate_chain_greeks,
                    chain=chain,
                    spot=self._current_price,
                    expiration=expiration,
                    risk_free_rate=self._risk_free_rate,
                    dividend_yield=self._current_dividend_yield,
                )
            await chain_table.display_chain(
                chain, self._current_price, self._spread_thresholds
            )
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
    parser.add_argument(
        "--config-help",
        action="store_true",
        help="Show all configuration options and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.config_help:
        print_config_help()
        sys.exit(0)

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

    app = TenorTUI(
        provider=provider,
        spread_thresholds=config.spread_thresholds,
        greeks_config=config.greeks,
        fred_api_key=config.fred_api_key,
        refresh_config=config.refresh,
        app_config=config,
    )
    app.run()
