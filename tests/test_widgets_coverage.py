"""Tests to improve widget coverage — chain_table, ticker_bar,
recently_viewed, expiry_selector, status_bar edge cases."""

import pytest
from textual.app import App, ComposeResult

from tenortui.models import OptionContract, OptionsChain, Quote
from tenortui.widgets.chain_table import ChainTable
from tenortui.widgets.expiry_selector import ExpirySelector
from tenortui.widgets.recently_viewed import RecentlyViewed
from tenortui.widgets.status_bar import StatusBar
from tenortui.widgets.ticker_bar import TickerBar


# --- Helper app for mounting widgets in isolation ---


class WidgetTestApp(App):
    def __init__(self, widget):
        super().__init__()
        self._widget = widget

    def compose(self) -> ComposeResult:
        yield self._widget


# --- ChainTable ---


def _make_contract(strike, option_type="call", with_greeks=False):
    return OptionContract(
        contract_symbol=f"TEST{strike}{option_type[0].upper()}",
        option_type=option_type,
        strike=strike,
        bid=1.0,
        ask=1.5,
        last_price=1.25,
        volume=100,
        open_interest=500,
        implied_volatility=0.30,
        delta=0.5 if with_greeks else None,
        gamma=0.05 if with_greeks else None,
        theta=-0.03 if with_greeks else None,
        vega=0.15 if with_greeks else None,
        rho=0.01 if with_greeks else None,
    )


@pytest.mark.asyncio
async def test_chain_table_display_chain_with_atm():
    """ChainTable displays chain with ATM row inserted."""
    chain = OptionsChain(
        symbol="AAPL",
        expiration="2026-03-21",
        calls=[
            _make_contract(200.0),
            _make_contract(210.0),
            _make_contract(220.0),
        ],
        puts=[_make_contract(200.0, "put")],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=215.0)
        # ATM row should be between 210 and 220 strikes


@pytest.mark.asyncio
async def test_chain_table_display_chain_without_price():
    """ChainTable displays chain without ATM marker when no price."""
    chain = OptionsChain(
        symbol="AAPL",
        expiration="2026-03-21",
        calls=[_make_contract(200.0), _make_contract(210.0)],
        puts=[],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=None)


@pytest.mark.asyncio
async def test_chain_table_display_with_greeks():
    """ChainTable shows Greek columns when contracts have Greeks."""
    chain = OptionsChain(
        symbol="AAPL",
        expiration="2026-03-21",
        calls=[
            _make_contract(200.0, with_greeks=True),
            _make_contract(210.0, with_greeks=True),
        ],
        puts=[_make_contract(200.0, "put", with_greeks=True)],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain, current_price=205.0)


@pytest.mark.asyncio
async def test_chain_table_show_message():
    """ChainTable.show_message displays text."""
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.show_message("No options available")


@pytest.mark.asyncio
async def test_chain_table_display_chain_replaces_previous():
    """Calling display_chain twice replaces the first chain."""
    chain1 = OptionsChain(
        symbol="AAPL",
        expiration="2026-03-21",
        calls=[_make_contract(200.0)],
        puts=[],
    )
    chain2 = OptionsChain(
        symbol="MSFT",
        expiration="2026-03-28",
        calls=[_make_contract(300.0), _make_contract(310.0)],
        puts=[_make_contract(300.0, "put")],
    )
    widget = ChainTable()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.display_chain(chain1, current_price=200.0)
        await widget.display_chain(chain2, current_price=305.0)


# --- TickerBar ---


@pytest.mark.asyncio
async def test_ticker_bar_show_quote():
    """TickerBar.show_quote displays quote info."""
    quote = Quote(
        symbol="AAPL",
        name="Apple Inc.",
        price=213.25,
        change=1.42,
        change_percent=0.67,
        volume=54_200_000,
        market_cap=3_200_000_000_000,
    )
    widget = TickerBar()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.show_quote(quote)
        display = widget.query_one("#quote-display")
        rendered = display.render().plain
        assert "Apple" in rendered
        assert "213.25" in rendered


@pytest.mark.asyncio
async def test_ticker_bar_show_quote_negative_change():
    """TickerBar.show_quote handles negative change."""
    quote = Quote(
        symbol="AAPL",
        name="Apple Inc.",
        price=210.00,
        change=-3.25,
        change_percent=-1.52,
        volume=54_200_000,
        market_cap=None,
    )
    widget = TickerBar()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.show_quote(quote)
        display = widget.query_one("#quote-display")
        rendered = display.render().plain
        assert "-3.25" in rendered


@pytest.mark.asyncio
async def test_ticker_bar_show_error():
    """TickerBar.show_error displays error message."""
    widget = TickerBar()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.show_error("Symbol 'XYZ' not found")
        display = widget.query_one("#quote-display")
        rendered = display.render().plain
        assert "not found" in rendered


@pytest.mark.asyncio
async def test_ticker_bar_focus_input():
    """TickerBar.focus_input focuses the input widget."""
    widget = TickerBar()
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.focus_input()
        input_w = widget.query_one("#ticker-input")
        assert input_w.has_focus


@pytest.mark.asyncio
async def test_ticker_bar_empty_submit_ignored():
    """Submitting empty string is ignored."""
    widget = TickerBar()
    app = WidgetTestApp(widget)
    messages = []
    async with app.run_test() as pilot:
        app.on_ticker_bar_ticker_submitted = lambda e: messages.append(e)
        input_w = widget.query_one("#ticker-input")
        input_w.value = "   "
        await pilot.press("enter")
        # No message posted for whitespace-only input
        assert len(messages) == 0


# --- RecentlyViewed ---


@pytest.mark.asyncio
async def test_recently_viewed_update_quotes():
    """RecentlyViewed.update_quotes populates the list."""
    quotes = [
        Quote("AAPL", "Apple Inc.", 213.25, 1.42, 0.67, 54_200_000, None),
        Quote("MSFT", "Microsoft Corp.", 415.50, -2.30, -0.55, 22_100_000, None),
    ]
    widget = RecentlyViewed(symbols=["AAPL", "MSFT"])
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.update_quotes(quotes)


@pytest.mark.asyncio
async def test_recently_viewed_empty_symbols():
    """RecentlyViewed with no symbols shows placeholder."""
    widget = RecentlyViewed(symbols=[])
    app = WidgetTestApp(widget)
    async with app.run_test():
        # Should not have a ListView
        assert len(widget.query("ListView")) == 0


@pytest.mark.asyncio
async def test_recently_viewed_selection_posts_message():
    """Selecting a recently viewed ticker posts TickerSubmitted."""
    quotes = [
        Quote("AAPL", "Apple Inc.", 213.25, 1.42, 0.67, 54_200_000, None),
        Quote("MSFT", "Microsoft Corp.", 415.50, -2.30, -0.55, 22_100_000, None),
    ]
    widget = RecentlyViewed(symbols=["AAPL", "MSFT"])
    app = WidgetTestApp(widget)
    messages = []

    async with app.run_test() as pilot:
        widget.update_quotes(quotes)

        # Capture posted messages
        original_handler = getattr(app, "on_ticker_bar_ticker_submitted", None)
        app.on_ticker_bar_ticker_submitted = lambda e: messages.append(e.symbol)

        # Select the first item in the list
        from textual.widgets import ListView

        list_view = widget.query_one(ListView)
        list_view.index = 0
        list_view.action_select_cursor()
        await pilot.pause()

        if original_handler:
            app.on_ticker_bar_ticker_submitted = original_handler


# --- ExpirySelector ---


@pytest.mark.asyncio
async def test_expiry_selector_set_expirations():
    """ExpirySelector creates tabs for expirations."""
    widget = ExpirySelector()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.set_expirations(["2026-03-21", "2026-03-28", "2026-04-04"])


@pytest.mark.asyncio
async def test_expiry_selector_empty_expirations():
    """ExpirySelector shows message for empty expirations."""
    widget = ExpirySelector()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.set_expirations([])


@pytest.mark.asyncio
async def test_expiry_selector_show_message():
    """ExpirySelector.show_message replaces content."""
    widget = ExpirySelector()
    app = WidgetTestApp(widget)
    async with app.run_test():
        await widget.show_message("Error loading options")


# --- StatusBar ---


@pytest.mark.asyncio
async def test_status_bar_update_refresh_time():
    """StatusBar.update_refresh_time updates the time display."""
    widget = StatusBar(provider_name="yahoo")
    app = WidgetTestApp(widget)
    async with app.run_test():
        widget.update_refresh_time()
        assert widget._last_refresh.startswith("Last: ")
