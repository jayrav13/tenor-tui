import pytest

from tenortui.app import TenorTUI
from tenortui.watchlists import WatchlistData, Watchlist, WatchlistItem
from tenortui.widgets.watchlist_panel import WatchlistPanel
from tenortui.widgets.chain_table import ChainTable


@pytest.fixture
def app(fake_provider, monkeypatch):
    monkeypatch.setattr(
        "tenortui.app.migrate_from_history",
        lambda: WatchlistData(watchlists=[Watchlist(name="Default")]),
    )
    monkeypatch.setattr("tenortui.app.save_watchlists", lambda data, **kw: None)
    return TenorTUI(provider=fake_provider)


@pytest.mark.asyncio
async def test_app_launches(app):
    async with app.run_test():
        assert app.title == "TenorTUI"


@pytest.mark.asyncio
async def test_search_ticker(app):
    async with app.run_test() as pilot:
        app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await app.workers.wait_for_complete()

        from tenortui.widgets.ticker_bar import TickerBar

        ticker_bar = app.query_one(TickerBar)
        display = ticker_bar.query_one("#quote-display")
        rendered = display.render().plain
        assert "Apple" in rendered or "213.25" in rendered


@pytest.mark.asyncio
async def test_focus_search(app):
    async with app.run_test() as pilot:
        await pilot.press("slash")
        from tenortui.widgets.ticker_bar import TickerBar

        input_widget = app.query_one(TickerBar).query_one("#ticker-input")
        assert input_widget.has_focus


@pytest.mark.asyncio
async def test_watchlist_panel_hidden_when_no_items(fake_provider, monkeypatch):
    monkeypatch.setattr(
        "tenortui.app.migrate_from_history",
        lambda: WatchlistData(watchlists=[Watchlist(name="Default")]),
    )
    test_app = TenorTUI(provider=fake_provider)
    async with test_app.run_test():
        wp = test_app.query_one(WatchlistPanel)
        assert wp.display is False


@pytest.mark.asyncio
async def test_watchlist_panel_shown_when_items_exist(fake_provider, monkeypatch):
    monkeypatch.setattr(
        "tenortui.app.migrate_from_history",
        lambda: WatchlistData(
            watchlists=[
                Watchlist(
                    name="Default",
                    items=[
                        WatchlistItem(type="equity", symbol="AAPL"),
                        WatchlistItem(type="equity", symbol="MSFT"),
                    ],
                )
            ]
        ),
    )
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [])
    test_app = TenorTUI(provider=fake_provider)
    async with test_app.run_test():
        wp = test_app.query_one(WatchlistPanel)
        ct = test_app.query_one(ChainTable)
        assert wp.display is True
        assert ct.display is False


@pytest.mark.asyncio
async def test_watchlist_panel_hidden_after_ticker_load(fake_provider, monkeypatch):
    monkeypatch.setattr(
        "tenortui.app.migrate_from_history",
        lambda: WatchlistData(
            watchlists=[
                Watchlist(
                    name="Default", items=[WatchlistItem(type="equity", symbol="AAPL")]
                )
            ]
        ),
    )
    monkeypatch.setattr("tenortui.app.batch_quotes", lambda syms: [])
    monkeypatch.setattr("tenortui.app.save_watchlists", lambda data, **kw: None)
    test_app = TenorTUI(provider=fake_provider)
    async with test_app.run_test() as pilot:
        test_app.action_focus_search()
        await pilot.press(*"AAPL")
        await pilot.press("enter")
        await test_app.workers.wait_for_complete()
        wp = test_app.query_one(WatchlistPanel)
        assert wp.display is False
