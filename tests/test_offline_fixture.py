"""The fixture provider is an offline, ephemeral demo mode (#62).

It must not call Yahoo, and must not read or write the user's watchlists.
"""

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

import tenortui.app as app_mod
from tenortui.app import TenorTUI
from tenortui.providers.fixture import FixtureProvider
from tenortui.watchlists import Watchlist, WatchlistData, WatchlistItem
from tenortui.widgets.fundamentals_bar import FundamentalsBar
from tenortui.widgets.watchlist_panel import WatchlistPanel

REPO = Path(__file__).resolve().parents[1]


def _private_data() -> WatchlistData:
    return WatchlistData(
        watchlists=[
            Watchlist(
                name="MySecretPortfolio",
                items=[WatchlistItem(type="equity", symbol="TSLA")],
            )
        ]
    )


@pytest.fixture
def spies(monkeypatch):
    """Record every persistence and Yahoo call the app makes."""
    calls = {"migrate": 0, "save": 0, "fundamentals": [], "batch": []}

    def migrate(*args, **kwargs):
        calls["migrate"] += 1
        return _private_data()

    def save(data, *args, **kwargs):
        calls["save"] += 1

    def fundamentals(quote):
        calls["fundamentals"].append(quote.symbol)
        quote.pe_ratio = 999.0
        return quote

    def batch(symbols):
        calls["batch"].append(list(symbols))
        return []

    monkeypatch.setattr(app_mod, "migrate_from_history", migrate)
    monkeypatch.setattr(app_mod, "save_watchlists", save)
    monkeypatch.setattr(app_mod, "fetch_fundamentals", fundamentals)
    monkeypatch.setattr(app_mod, "batch_quotes", batch)
    return calls


def test_fixture_provider_is_offline():
    assert FixtureProvider.offline is True


@pytest.mark.asyncio
async def test_fixture_does_not_fetch_fundamentals(spies):
    app = TenorTUI(provider=FixtureProvider())
    async with app.run_test(size=(140, 40)) as pilot:
        app._load_ticker("AAPL")
        await pilot.pause(delay=1.0)
        text = str(app.query_one(FundamentalsBar).query_one("Static").render())
    assert spies["fundamentals"] == []
    assert "P/E: 31.35" in text


@pytest.mark.asyncio
async def test_fixture_does_not_read_or_write_watchlists(spies):
    app = TenorTUI(provider=FixtureProvider())
    async with app.run_test(size=(140, 40)):
        data = app._watchlist_data
        assert [wl.name for wl in data.watchlists] == ["Default"]
        assert data.watchlists[0].items == []
        # Edits stay in memory and are not persisted.
        app._pending_watchlist_item = WatchlistItem(type="equity", symbol="AAPL")
        app._on_watchlist_picked(0)
        assert data.watchlists[0].items[0].symbol == "AAPL"
    assert spies["migrate"] == 0
    assert spies["save"] == 0


@pytest.mark.asyncio
async def test_fixture_watchlist_prices_come_from_provider(spies):
    app = TenorTUI(provider=FixtureProvider())
    async with app.run_test(size=(140, 40)) as pilot:
        app._watchlist_data.watchlists[0].items.append(
            WatchlistItem(type="equity", symbol="AAPL")
        )
        app._fetch_watchlist_quotes()
        await pilot.pause(delay=0.5)
        panel = app.query_one(WatchlistPanel)
        assert panel._equity_quotes["AAPL"].price == 213.25
    assert spies["batch"] == []


@pytest.mark.asyncio
async def test_online_provider_still_fetches_and_persists(spies, fake_provider):
    app = TenorTUI(provider=fake_provider)
    async with app.run_test(size=(140, 40)) as pilot:
        assert app._watchlist_data.watchlists[0].name == "MySecretPortfolio"
        await pilot.pause(delay=0.3)
        app._load_ticker("AAPL")
        await pilot.pause(delay=1.0)
        app._pending_watchlist_item = WatchlistItem(type="equity", symbol="AAPL")
        app._on_watchlist_picked(0)
    assert spies["migrate"] == 1
    assert spies["fundamentals"] == ["AAPL"]
    assert spies["batch"] == [["TSLA"]]
    assert spies["save"] == 1


@pytest.mark.asyncio
async def test_bin_snapshot_does_not_leak_user_watchlists(spies, tmp_path, monkeypatch):
    loader = importlib.machinery.SourceFileLoader(
        "snapshot_mod", str(REPO / "bin" / "snapshot")
    )
    spec = importlib.util.spec_from_loader("snapshot_mod", loader)
    snap = importlib.util.module_from_spec(spec)
    loader.exec_module(snap)
    monkeypatch.setattr(snap, "OUTPUT_DIR", tmp_path / "out")
    path = await snap._run_snapshot("watchlist-modal", snap.watchlist_modal)
    assert "MySecretPortfolio" not in path.read_text()
    assert spies["migrate"] == 0
    assert spies["save"] == 0
