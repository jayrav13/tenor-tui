"""Manual refresh (r / Ctrl+R) keeps the selected expiry (#61)."""

import pytest
from textual.widgets import TabbedContent

from tenortui.app import TenorTUI
from tenortui.models import OptionsChain
from tenortui.watchlists import WatchlistData, Watchlist
from tenortui.widgets.expiry_selector import ExpirySelector


class RecordingProvider:
    """Provider that records chain requests and allows swapping expirations."""

    name = "recording"

    def __init__(self, quote, expirations):
        self._quote = quote
        self.expirations = list(expirations)
        self.chain_calls: list[str] = []

    def get_quote(self, symbol):
        return self._quote

    def get_expirations(self, symbol):
        return list(self.expirations)

    def get_chain(self, symbol, expiration):
        self.chain_calls.append(expiration)
        return OptionsChain(symbol=symbol, expiration=expiration, calls=[], puts=[])


@pytest.fixture
def provider(sample_quote, sample_expirations):
    return RecordingProvider(sample_quote, sample_expirations)


@pytest.fixture
def app(provider, monkeypatch):
    monkeypatch.setattr(
        "tenortui.app.migrate_from_history",
        lambda: WatchlistData(watchlists=[Watchlist(name="Default")]),
    )
    monkeypatch.setattr("tenortui.app.save_watchlists", lambda data: None)
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda symbols: {})
    monkeypatch.setattr("tenortui.app.fetch_fundamentals", lambda quote: quote)
    monkeypatch.setattr(
        "tenortui.app.get_risk_free_rate", lambda *a, **kw: (0.045, False)
    )
    a = TenorTUI(provider=provider)
    a._auto_refresh_enabled = False
    return a


async def _settle(app, pilot):
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


async def _load_and_select(app, pilot, index):
    app._current_symbol = "AAPL"
    app._load_ticker("AAPL")
    await _settle(app, pilot)
    tabbed = app.query_one(ExpirySelector).query_one(TabbedContent)
    tab_ids = [p.id for p in tabbed.query("TabPane")]
    tabbed.active = tab_ids[index]
    await _settle(app, pilot)
    return tabbed


def _active_label(app):
    tabbed = app.query_one(ExpirySelector).query_one(TabbedContent)
    return str(tabbed.get_tab(tabbed.active).label)


@pytest.mark.asyncio
async def test_manual_refresh_keeps_selected_expiry(app, provider, sample_expirations):
    async with app.run_test() as pilot:
        await _load_and_select(app, pilot, 2)
        assert app._current_expiration == sample_expirations[2]
        calls_before = len(provider.chain_calls)

        app.action_refresh()
        await _settle(app, pilot)

        assert app._current_expiration == sample_expirations[2]
        assert provider.chain_calls[calls_before:] == [sample_expirations[2]]
        assert _active_label(app) == sample_expirations[2]


@pytest.mark.asyncio
async def test_manual_refresh_falls_back_when_expiry_gone(
    app, provider, sample_expirations
):
    async with app.run_test() as pilot:
        await _load_and_select(app, pilot, 2)

        provider.expirations = [
            e for e in sample_expirations if e != sample_expirations[2]
        ]
        app.action_refresh()
        await _settle(app, pilot)

        assert app._current_expiration == sample_expirations[0]
        assert provider.chain_calls[-1] == sample_expirations[0]
        assert _active_label(app) == sample_expirations[0]


@pytest.mark.asyncio
async def test_new_ticker_search_selects_first_expiry(
    app, provider, sample_expirations
):
    async with app.run_test() as pilot:
        await _load_and_select(app, pilot, 2)

        app._load_ticker("MSFT")
        await _settle(app, pilot)

        assert app._current_expiration == sample_expirations[0]
        assert provider.chain_calls[-1] == sample_expirations[0]
        assert _active_label(app) == sample_expirations[0]
