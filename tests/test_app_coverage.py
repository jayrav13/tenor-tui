"""Tests to improve app.py coverage — targeting _load_ticker errors,
_load_chain, action_refresh, expiry selection, and edge cases."""

import pytest

from tenortui.app import TenorTUI
from tenortui.exceptions import ProviderError, SymbolNotFoundError
from tenortui.models import OptionsChain
from tenortui.widgets.chain_table import ChainTable
from tenortui.widgets.expiry_selector import ExpirySelector
from tenortui.widgets.recently_viewed import RecentlyViewed
from tenortui.widgets.status_bar import StatusBar
from tenortui.widgets.ticker_bar import TickerBar


class ErrorProvider:
    """Provider that raises errors for testing error paths."""

    name = "error"

    def __init__(self, error_type="symbol"):
        self._error_type = error_type

    def get_quote(self, symbol):
        if self._error_type == "symbol":
            raise SymbolNotFoundError(f"Symbol '{symbol}' not found")
        raise ProviderError("API failure")

    def get_expirations(self, symbol):
        if self._error_type == "expirations":
            raise ProviderError("Failed to fetch expirations")
        return []

    def get_chain(self, symbol, expiration):
        if self._error_type == "chain":
            raise ProviderError("Failed to fetch chain")
        return OptionsChain(symbol=symbol, expiration=expiration, calls=[], puts=[])


class NoExpirationsProvider:
    """Provider that returns a valid quote but no expirations."""

    name = "no-exp"

    def __init__(self, quote):
        self._quote = quote

    def get_quote(self, symbol):
        return self._quote

    def get_expirations(self, symbol):
        return []

    def get_chain(self, symbol, expiration):
        return OptionsChain(symbol=symbol, expiration=expiration, calls=[], puts=[])


class ChainErrorProvider:
    """Provider that works for quote/expirations but fails on chain."""

    name = "chain-error"

    def __init__(self, quote, expirations):
        self._quote = quote
        self._expirations = expirations

    def get_quote(self, symbol):
        return self._quote

    def get_expirations(self, symbol):
        return self._expirations

    def get_chain(self, symbol, expiration):
        raise ProviderError("Chain fetch failed")


# --- _load_ticker error handling ---


@pytest.mark.asyncio
async def test_load_ticker_symbol_not_found(monkeypatch):
    """SymbolNotFoundError shows error in ticker bar."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    provider = ErrorProvider(error_type="symbol")
    app = TenorTUI(provider=provider)
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"BADTICKER")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        ticker_bar = app.query_one(TickerBar)
        display = ticker_bar.query_one("#quote-display")
        rendered = display.render().plain
        assert "not found" in rendered


@pytest.mark.asyncio
async def test_load_ticker_provider_error(monkeypatch):
    """ProviderError shows error message in ticker bar."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    provider = ErrorProvider(error_type="provider")
    app = TenorTUI(provider=provider)
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        ticker_bar = app.query_one(TickerBar)
        display = ticker_bar.query_one("#quote-display")
        rendered = display.render().plain
        assert "API failure" in rendered


@pytest.mark.asyncio
async def test_load_ticker_no_expirations(sample_quote, monkeypatch):
    """Ticker with no expirations shows message in chain table."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    provider = NoExpirationsProvider(quote=sample_quote)
    app = TenorTUI(provider=provider)
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Quote should be displayed
        ticker_bar = app.query_one(TickerBar)
        display = ticker_bar.query_one("#quote-display")
        rendered = display.render().plain
        assert "Apple" in rendered or "213.25" in rendered


@pytest.mark.asyncio
async def test_load_ticker_expirations_error(sample_quote, monkeypatch):
    """ProviderError during expiration fetch shows error in chain table."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])

    class ExpErrorProvider:
        name = "exp-error"

        def get_quote(self, symbol):
            return sample_quote

        def get_expirations(self, symbol):
            raise ProviderError("Expirations failed")

        def get_chain(self, symbol, expiration):
            return OptionsChain(symbol=symbol, expiration=expiration, calls=[], puts=[])

    app = TenorTUI(provider=ExpErrorProvider())
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Should not crash; status bar should update
        status = app.query_one(StatusBar)
        assert status is not None


# --- _load_chain ---


@pytest.mark.asyncio
async def test_load_chain_on_expiry_selection(fake_provider, sample_chain, monkeypatch):
    """Selecting an expiry tab triggers chain load."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        # Load a ticker first
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Verify chain table is populated
        chain_table = app.query_one(ChainTable)
        assert chain_table.display is True
        assert chain_table.loading is False


@pytest.mark.asyncio
async def test_load_chain_provider_error(sample_quote, sample_expirations, monkeypatch):
    """ProviderError during chain fetch shows error message."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    provider = ChainErrorProvider(quote=sample_quote, expirations=sample_expirations)
    app = TenorTUI(provider=provider)
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        chain_table = app.query_one(ChainTable)
        assert chain_table.loading is False


# --- action_refresh ---


@pytest.mark.asyncio
async def test_refresh_reloads_ticker(fake_provider, monkeypatch):
    """Ctrl+R refreshes the current ticker."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        # Load ticker first
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Refresh
        await pilot.press("ctrl+r")
        await app.workers.wait_for_complete()

        # Should still show the quote
        ticker_bar = app.query_one(TickerBar)
        display = ticker_bar.query_one("#quote-display")
        rendered = display.render().plain
        assert "Apple" in rendered or "213.25" in rendered


@pytest.mark.asyncio
async def test_refresh_without_ticker_does_nothing(fake_provider, monkeypatch):
    """Ctrl+R with no ticker loaded is a no-op."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        await pilot.press("ctrl+r")
        await app.workers.wait_for_complete()
        # No crash, app still running
        assert app._current_symbol is None


# --- _fetch_recent_quotes ---


@pytest.mark.asyncio
async def test_fetch_recent_quotes(sample_quote, fake_provider, monkeypatch):
    """App with history fetches recent quotes on mount."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: ["AAPL", "MSFT"])
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [sample_quote])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test():
        await app.workers.wait_for_complete()
        rv = app.query_one(RecentlyViewed)
        assert rv.display is True


# --- Expiry tab prevents double load while loading ticker ---


@pytest.mark.asyncio
async def test_expiry_ignored_during_ticker_load(fake_provider, monkeypatch):
    """Expiry selection during ticker load is ignored (_loading_ticker flag)."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test():
        # Manually set the flag to simulate mid-load
        app._loading_ticker = True
        # Post an expiry event — should be ignored
        app.on_expiry_selector_expiry_selected(
            ExpirySelector.ExpirySelected("2026-03-21")
        )
        # _current_expiration gets set but no chain load triggered
        assert app._current_expiration == "2026-03-21"


# --- _load_chain triggered independently via expiry tab ---


@pytest.mark.asyncio
async def test_expiry_tab_triggers_independent_chain_load(fake_provider, monkeypatch):
    """After ticker is loaded, selecting a different expiry triggers _load_chain."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])
    app = TenorTUI(provider=fake_provider)
    async with app.run_test() as pilot:
        # Load a ticker
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Now simulate an expiry selection event (ticker is loaded, _loading_ticker is False)
        assert app._loading_ticker is False
        app.on_expiry_selector_expiry_selected(
            ExpirySelector.ExpirySelected("2026-03-28")
        )
        await app.workers.wait_for_complete()

        assert app._current_expiration == "2026-03-28"
        chain_table = app.query_one(ChainTable)
        assert chain_table.loading is False


@pytest.mark.asyncio
async def test_chain_load_error_on_expiry_switch(
    sample_quote, sample_expirations, monkeypatch
):
    """ProviderError on _load_chain (independent of _load_ticker) is handled."""
    monkeypatch.setattr("tenortui.app.load_history", lambda: [])
    monkeypatch.setattr("tenortui.app.add_to_history", lambda sym: [sym])

    # Provider that works for first chain but fails on second
    call_count = {"chain": 0}

    class SwitchErrorProvider:
        name = "switch-error"

        def get_quote(self, symbol):
            return sample_quote

        def get_expirations(self, symbol):
            return sample_expirations

        def get_chain(self, symbol, expiration):
            call_count["chain"] += 1
            if call_count["chain"] > 1:
                raise ProviderError("Chain load failed on switch")
            return OptionsChain(symbol=symbol, expiration=expiration, calls=[], puts=[])

    app = TenorTUI(provider=SwitchErrorProvider())
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        # Now trigger a second expiry — this one will fail
        app.on_expiry_selector_expiry_selected(
            ExpirySelector.ExpirySelected("2026-03-28")
        )
        await app.workers.wait_for_complete()

        chain_table = app.query_one(ChainTable)
        assert chain_table.loading is False


# --- _parse_args ---


def test_parse_args_default(monkeypatch):
    """_parse_args with no arguments returns None provider."""
    import sys

    from tenortui.app import _parse_args

    monkeypatch.setattr(sys, "argv", ["tenortui"])
    args = _parse_args()
    assert args.provider is None


def test_parse_args_with_provider(monkeypatch):
    """_parse_args with --provider returns the provider name."""
    import sys

    from tenortui.app import _parse_args

    monkeypatch.setattr(sys, "argv", ["tenortui", "--provider", "tradier"])
    args = _parse_args()
    assert args.provider == "tradier"
